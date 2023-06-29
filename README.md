# Unofficial update to Autodesk 3DS Import/Export for Blender 3.x

### NOTE: Export is currently broken.

## Description

This Blender plugin is an unofficial update of the official 2.79 3DS file import/export plugin. This updated plugin is compatible with Blender versions from 3.x onwards.

## Installation

1. Clone the repository to the following directory: `3.x\scripts\addons\io_scene_3ds`. Ensure you have the necessary permissions to clone the repository in this directory.
2. In Blender, navigate to `Edit` -> `Preferences`.
3. Click on `Add-ons`.
4. In the Add-ons tab, find `Import-Export: Autodesk 3DS Format` and enable the add-on by checking the box next to it.

## Game File Support

This extended version of the plugin adds support for game-specific file formats. Specifically, the following games are supported:

- Hidden and Dangerous 1: The plugin allows importing of Insanity3D I3D files (See Limitations)

More game file formats will be added in the future.

## Usage

1. To import a 3DS or I3D file, navigate to `File` -> `Import` -> `3D Studio (.3ds) EXPERIMENTAL`.
2. In the file dialog, select the 3DS or I3D file you wish to import.
3. Click `Import`.

## Limitations

Please note that the focus of this plugin is mainly on the importing functionality. The exporting functionality for both 3DS and I3D files is currently under development and may not work as expected.

Another important issue to note is that importing UV maps from I3D files is currently not functioning correctly. This is a known issue, and we are working to fix it in future updates.

In addition, the transformations in imported models are only partially working and might not accurately reflect the original model. We are aware of this limitation and are actively working on a solution.

Contributions to improve these features are most welcome.

## Troubleshooting

If you encounter any issues or have any questions, please file an issue on the GitHub repository.

## Contributing

Contributions are welcome! If you'd like to contribute, please fork the repository and make changes as you'd like. Pull requests are warmly welcome.

## License

This project is licensed under the MIT License.
