import argparse
import os
import glob
import platform
import logging
import shutil
import subprocess
import os.path as osp
import distutils.file_util as file_util
import xml.etree.ElementTree as ElementTree

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger()

_root_dir = osp.abspath(osp.join(osp.dirname(__file__), os.pardir))
_builds_dir = osp.join(_root_dir, 'Builds')


def parse_jucer() -> tuple[str, str, ElementTree.Element]:
    jucer_files = glob.glob(osp.join(_root_dir, '*.jucer'))
    if not jucer_files:
        raise FileNotFoundError(f'Can not found *.jucer file under: {_root_dir}')

    target = jucer_files[0]
    logger.info(f'Target juce project: {target}')
    root = ElementTree.parse(target).getroot()

    return root.get('name'), root.get('version'), root.find('EXPORTFORMATS')


class Worker:
    def __init__(self, args):
        self.args = args
        self.platformTag = None
        self.defaultVst3Dir = None
        self.outputVst3FullPath = None
        self.pluginBasename, self.version, self.exporters = parse_jucer()
        self.exporter = None
        self.defaultExportPrefix = None

    @staticmethod
    def create_platform(args):
        current_system = platform.system()
        if current_system == 'Windows':
            return WindowsWorker(args)
        if current_system == 'Darwin':
            return MacWorker(args)

        raise NotImplementedError(f'Unsupported platform: {current_system}!')

    def main(self):
        self._find_exporter()
        self._set_output_vst3_fullpath()
        self._build()
        self._copy_to_vst3_dir()
        self._make_archive()

    def _find_exporter(self):
        if self.args.exporter:
            self.exporter = self.exporters.find(self.args.exporter)
        if self.exporter:
            return

        # When exporter is not assigned or not found.
        for exporter in self.exporters:
            if exporter.tag.startswith(self.defaultExportPrefix):
                self.exporter = exporter
                break

        if not self.exporter:
            raise ValueError('Can not find vs exporter.')

    def _set_output_vst3_fullpath(self):
        raise NotImplementedError('Subclass it.')

    def _build(self):
        raise NotImplementedError('Subclass it.')

    def _copy_to_vst3_dir(self):
        if not (self.args.copyToVst3Dir and self.defaultVst3Dir and self.outputVst3FullPath):
            return

        logger.info('=====Copy to vst3 dir=====')
        logger.info(f'target dir: {self.defaultVst3Dir}')
        os.makedirs(self.defaultVst3Dir, exist_ok=True)

        if not osp.isfile(self.outputVst3FullPath):
            raise FileNotFoundError(f'Can not find build output: {self.outputVst3FullPath}, check build log.')

        dst = osp.join(self.defaultVst3Dir, f'{self.pluginBasename}.vst3')
        file_util.copy_file(self.outputVst3FullPath, dst)
        logger.info(f'Copy file: {self.outputVst3FullPath} => {dst}')

    def _make_archive(self):
        if not self.args.distribute:
            return

        logger.info('=====Make archive=====')
        archive_basename = f'{self.pluginBasename}_{self.platformTag}_v{self.version}'
        dist_dir = osp.join(_root_dir, 'dist')
        os.makedirs(dist_dir, exist_ok=True)
        shutil.make_archive(
            osp.join(dist_dir, archive_basename),
            'zip',
            root_dir=osp.dirname(self.outputVst3FullPath),
            base_dir=osp.basename(self.outputVst3FullPath),
            logger=logger
        )


class WindowsWorker(Worker):
    def __init__(self, args):
        super().__init__(args)
        self.platformTag = 'win'
        self.defaultVst3Dir = osp.join(os.getenv('CommonProgramW6432'), 'VST3')
        self.defaultExportPrefix = 'VS'

    def _set_output_vst3_fullpath(self):
        self.outputVst3FullPath = osp.join(_root_dir, self.exporter.get('targetFolder'), 'x64', self.args.config,
                                           'VST3', f'{self.pluginBasename}.vst3')

    def _build(self):
        logger.info('=====Build=====')
        # Check if msbuild is in env path.
        cmd = [
            'where',
            'msbuild'
        ]
        subprocess.run(cmd, check=True)

        # build shared code
        cmd = [
            'msbuild',
            f'Builds\\VisualStudio2022\\{self.pluginBasename}_SharedCode.vcxproj',
            f'/property:Configuration={self.args.config},Platform=x64'
        ]
        subprocess.run(cmd, check=True, cwd=_root_dir)

        # build vst3
        cmd = [
            'msbuild',
            f'Builds\\VisualStudio2022\\{self.pluginBasename}_VST3.vcxproj',
            f'/property:Configuration={self.args.config},Platform=x64'
        ]
        subprocess.run(cmd, check=True, cwd=_root_dir)


class MacWorker(Worker):
    def __init__(self, args):
        super().__init__(args)
        self.platformTag = 'mac'
        self.defaultVst3Dir = '/Library/Audio/Plug-Ins/VST3'
        self.outputVst3FullPath = None
        self.defaultExportPrefix = 'XCODE_MAC'

    def _set_output_vst3_fullpath(self):
        # TODO: verify this
        self.outputVst3FullPath = osp.join(_root_dir, self.exporter.get('targetFolder'), 'build', self.args.config,
                                           'VST3', f'{self.pluginBasename}.vst3')

    def _build(self):
        # TODO: impl this.
        pass


def validate_args(args) -> bool:
    if args.config != 'Release' and args.distribute:
        res = input(f'Attempt to distribute as {args.config} build. Continue? (y/n)')
        if res.lower() == 'y':
            return True
        logging.info('Canceled.')
        return False

    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Juce vst3 plugin build tool.')
    parser.add_argument(
        '-c',
        '--config',
        dest='config',
        default='Release',
        choices=('Release', 'Debug'),
        action='store',
        help='Build config, default to be "Release".'
    )
    parser.add_argument(
        '-C',
        '--copy-to-vst3-dir',
        dest='copyToVst3Dir',
        default=False,
        action='store_true',
        help='Copy .vst3 file to default vst3 directory. "%%CommonProgramW6432%%\\VST3" on windows.'
    )
    parser.add_argument(
        '-d',
        '--distribute',
        dest='distribute',
        default=False,
        action='store_true',
        help='Archive vst3 as zip file with version tag and save it to "dist" folder.'
    )
    parser.add_argument(
        '-e',
        '--exporter',
        dest='exporter',
        default=None,
        action='store',
        help='Assign juce exporter, which is defined between EXPORTFORMATS tag in .jucer file. If not set, '
             'will use first exporters in current platform(VS for windows and xcode for mac).'
    )
    parsed_args = parser.parse_args()

    if validate_args(parsed_args):
        worker = Worker.create_platform(parsed_args)
        worker.main()
