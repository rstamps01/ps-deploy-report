# VSCode Configuration for VAST As-Built Report Generator

This directory contains VSCode configuration files to provide an optimal development environment for the VAST As-Built Report Generator project.

## Configuration Files

### `settings.json`
- Python interpreter configuration pointing to the virtual environment
- Code formatting with Black (88 character line length)
- Linting with Flake8
- Testing configuration with pytest
- File exclusions for cache files and virtual environments
- Editor settings for consistent code style

### `launch.json`
- **Python: Current File** - Run the currently open Python file
- **Python: Main Module** - Run the main application with example arguments
- **Python: Test Current File** - Run tests for the current file
- **Python: Run All Tests** - Run all tests in the project
- **Python: Validate Environment** - Run the environment validation script
- **Python: Test Logging** - Run the logging test script

### `tasks.json`
- **Install Dependencies** - Install Python packages from requirements.txt
- **Run Tests** - Execute all tests with pytest
- **Run Tests with Coverage** - Run tests with coverage reporting
- **Lint Code** - Run Flake8 linting
- **Format Code** - Format code with Black
- **Validate Environment** - Run environment validation
- **Create Virtual Environment** - Create a new virtual environment
- **Activate Virtual Environment** - Activate the virtual environment
- **Clean Python Cache** - Remove Python cache files
- **Generate Report (Example)** - Run the main application with example arguments

### `extensions.json`
Recommended VSCode extensions for Python development:
- Python language support
- Pylance (Python language server)
- Black formatter
- Flake8 linter
- pytest test runner
- isort import sorter
- YAML support
- Markdown support
- PDF viewer
- Git integration tools

### `c_cpp_properties.json`
C/C++ configuration for any native extensions or C code in the project.

### `keybindings.json`
Custom keyboard shortcuts for common development tasks.

### `snippets.json`
Code snippets for common Python patterns:
- Test functions with arrange-act-assert pattern
- Class definitions
- Function definitions
- Main execution guards
- Import statements
- Try-except blocks
- Logging setup

## Workspace File

The project also includes a `ps-deploy-report.code-workspace` file that can be opened directly in VSCode to load the entire project with all configurations.

## Usage

1. Open VSCode in the project directory
2. VSCode will automatically detect the Python interpreter in the virtual environment
3. Use `Ctrl+Shift+P` to access the command palette
4. Use `F5` to start debugging
5. Use `Ctrl+Shift+` ` to open a new terminal
6. Use `Ctrl+Shift+P` and type "Tasks: Run Task" to access build tasks

## Development Workflow

1. **Setup**: Run the "Create Virtual Environment" task, then "Install Dependencies"
2. **Development**: Write code with automatic formatting and linting
3. **Testing**: Use "Run Tests" task or the debug configurations
4. **Code Quality**: Use "Format Code" and "Lint Code" tasks
5. **Debugging**: Use the launch configurations for debugging specific parts of the application

## Troubleshooting

- If Python interpreter is not detected, check that the virtual environment exists and is properly configured
- If extensions are not working, ensure they are installed from the recommendations
- If tasks fail, ensure the virtual environment is activated and dependencies are installed
- For debugging issues, check the Python path configuration in launch.json

## Customization

All configuration files can be customized to match your specific development preferences. The settings are designed to work well with the project's coding standards and requirements.
