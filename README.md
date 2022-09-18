# juci
Personal cli ci build tool for juce plugin dev.

## feature
- cli for
  - Build plugin
  - Copy to system vst3 directory
  - Archive vst3 as zip with version tag.

## How to use
### Deployment
#### Git repo
- Run this command in your juce project dir to add juci as a submodule.
  ```
  git submodule add git@github.com:tgalpha/juci.git
  ```

#### Local only
- Copy this repo into your juce project root dir.
  ```
  - your_plugin_directory
    - juci  <--- Here
    - your_plugin.jucer
    - ...
  ```
### Use
- Get args help.
  ```
  juci.bat -h
  ```
- Build with copy .vst3 to system path.
  ```
  juci.bat -C
  ```
- Build and make archive with version tag.
  ```
  juci.bat -d
  ```
