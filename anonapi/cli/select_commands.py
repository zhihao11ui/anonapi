"""Click group and commands for the 'select' subcommand
"""
import os
from pathlib import Path

import click

from anonapi.cli.parser import command_group_function, echo_error
from anonapi.context import AnonAPIContext
from anonapi.selection import FileFolder, open_as_dicom
from fileselection.fileselection import FileSelectionFolder, FileSelectionFile
from tqdm import tqdm


class CLIMessages:
    NO_SELECTION_DEFINED = "There is no selection defined in current folder"


class SelectCommandContext:
    def __init__(self, current_path):
        self.current_path = Path(current_path)

    def get_current_selection_folder(self):
        return FileSelectionFolder(self.current_path)

    def get_current_selection(self):
        """Load selection in current folder

        Returns
        -------
        FileSelectionFile

        Raises
        ------
        FileNotFoundError
            When there is no selection in current folder

        """

        return self.get_current_selection_folder().load_file_selection()


def describe_selection(selection):
    """Create a human readable description of the given selection

    Parameters
    ----------
    selection: FileSelectionFile


    Returns
    -------
    str

    """
    return (
        f"Selection containing {len(selection.selected_paths)} files:\n"
        f"Description: {selection.description}"
    )


@click.group(name="select")
@click.pass_context
def main(ctx):
    """select files for a single anonymization job"""
    parser: AnonAPIContext = ctx.obj
    context = SelectCommandContext(current_path=parser.current_dir())
    ctx.obj = context


@command_group_function()
def status(context: SelectCommandContext):
    """Show selection in current directory"""
    try:
        selection = context.get_current_selection()
        click.echo(describe_selection(selection))
    except FileNotFoundError as e:
        echo_error(CLIMessages.NO_SELECTION_DEFINED)


@command_group_function()
def delete(context: SelectCommandContext):
    """Show selection in current directory"""

    selection_folder = context.get_current_selection_folder()
    if selection_folder.has_file_selection():
        os.remove(selection_folder.get_data_file_path())
        click.echo("Removed file selection in current folder")
    else:
        echo_error(CLIMessages.NO_SELECTION_DEFINED)


@command_group_function()
@click.argument("pattern", type=str)
@click.option("--recurse/--no-recurse", default=True, help="Recurse into directories")
@click.option(
    "--check-dicom/--no-check-dicom",
    default=False,
    help="Allows only DICOM files. Opens all files",
)
@click.option(
    "--exclude-pattern",
    "-e",
    multiple=True,
    help="Exclude any filepath matching this. * is wildcard.",
)
def add(context: SelectCommandContext, pattern, recurse, check_dicom,
        exclude_pattern):
    """Add all files matching given pattern to the selection in the current folder.

    Excludes 'fileselection.txt'
    """
    click.echo(f"Finding files...")
    current_folder = FileFolder(context.current_path)
    paths = list(
        tqdm(
            current_folder.iterate(
                pattern=pattern,
                recurse=recurse,
                exclude_patterns=["fileselection.txt"] + list(exclude_pattern),
            )
        )
    )

    if check_dicom:
        click.echo("Checking that each file is Dicom")
        paths = [x for x in tqdm(paths) if open_as_dicom(x)]

    selection_folder = context.get_current_selection_folder()
    if selection_folder.has_file_selection():
        selection = selection_folder.load_file_selection()
        selection.add(paths)
    else:
        selection = selection_folder.create_file_selection_file(
            description=selection_folder.path.name + " auto-generated by anonapi",
            selected_paths=paths,
        )

    selection.save_to_file()
    click.echo(f"selection now contains {len(selection.selected_paths)} files")


@command_group_function()
def edit(context: SelectCommandContext):
    """initialise a selection for the current directory, add all DICOM files"""

    selection_folder = context.get_current_selection_folder()
    if not selection_folder.has_file_selection():
        echo_error(CLIMessages.NO_SELECTION_DEFINED)
    else:
        click.launch(str(selection_folder.get_data_file_path()))


# TODO: replace this function
def create_dicom_selection_click(path):
    """Find all DICOM files path (recursive) and save them a FileSelectionFile.

    Meant to be included directly inside click commands. Uses a lot of click.echo()

    Parameters
    ----------
    path: PathLike
    """
    # Find all dicom files in this folder
    click.echo(f"Adding '{path}' to mapping")
    folder = FileFolder(path)
    click.echo(f"Finding all files in {path}")
    files = [x for x in tqdm(folder.iterate()) if x is not None]
    click.echo(f"Found {len(files)} files. Finding out which ones are DICOM")
    dicom_files = [x for x in tqdm(files) if open_as_dicom(x)]
    click.echo(f"Found {len(dicom_files)} DICOM files")
    # record dicom files as fileselection
    selection_folder = FileSelectionFolder(path=path)
    selection = FileSelectionFile(
        data_file_path=selection_folder.get_data_file_path(),
        description=Path(path).name + " auto-generated by anonapi",
        selected_paths=dicom_files,
    )
    selection_folder.save_file_selection(selection)


for func in [status, delete, edit, add]:
    main.add_command(func)
