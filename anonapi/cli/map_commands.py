"""Click group and commands for the 'map' subcommand
"""

import click
import datetime
import random
import string

from click.exceptions import BadParameter, UsageError, ClickException

from anonapi.cli.click_types import FileSelectionFileParam
from anonapi.cli.select_commands import create_dicom_selection_click
from anonapi.context import AnonAPIContext
from anonapi.decorators import pass_anonapi_context
from anonapi.mapper import (MappingListFolder, MappingList,
                            AnonymizationParameters, MappingLoadError,
                            ExampleMappingList, MapperException)
from anonapi.parameters import SourceIdentifierFactory


class MapCommandContext:
    def __init__(self, current_path):
        self.current_path = current_path

    def get_current_mapping_folder(self):
        return MappingListFolder(self.current_path)

    def get_current_mapping(self):
        """Load mapping from the current directory

        Returns
        -------
        MappingList
            Loaded from current dir

        Raises
        ------
        MappingLoadException
            When no mapping could be loaded from current directory

        """
        return self.get_current_mapping_folder().get_mapping()


pass_map_command_context = click.make_pass_decorator(MapCommandContext)


@click.group(name="map")
@click.pass_context
@pass_anonapi_context
def main(context: AnonAPIContext, ctx):
    """map original data to anonymized name, id, etc."""

    # both anonapi_context and base click ctx are passed to be able change ctx.obj
    ctx.obj = MapCommandContext(current_path=context.current_dir)


@click.command()
@pass_map_command_context
def status(context: MapCommandContext):
    """Show mapping in current directory"""
    try:
        mapping = context.get_current_mapping()
        click.echo(mapping.to_table_string())
    except MappingLoadError as e:
        raise ClickException(e)


@click.command()
@pass_map_command_context
def init(context: MapCommandContext):
    """Save a default mapping in the current folder"""
    folder = context.get_current_mapping_folder()
    mapping_list = ExampleMappingList()
    folder.save_list(mapping_list)
    click.echo(f"Initialised example mapping in {mapping_list.DEFAULT_FILENAME}")


@click.command()
@pass_map_command_context
def delete(context: MapCommandContext):
    """delete mapping in current folder"""
    folder = context.get_current_mapping_folder()
    if not folder.has_mapping_list():
        raise ClickException("No mapping defined in current folder")
        return
    folder.delete_list()
    click.echo(f"Removed mapping in current dir")


def get_mapping(context):
    try:
        return context.get_current_mapping()
    except MappingLoadError:
        raise UsageError("No mapping in current folder")


@click.command()
@pass_map_command_context
@click.argument("path", type=click.Path(exists=True))
def add_study_folder(context: MapCommandContext, path):
    """Add all dicom files in given folder to map
    """

    mapping = get_mapping(context)

    # create a selection from all dicom files in given path
    create_dicom_selection_click(path)

    # add this selection to mapping
    folder_source_id = SourceIdentifierFactory().get_source_identifier_for_key(f"folder:{path}")
    patient_name = f"autogenerated_{''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}"
    patient_id = "auto_" + "".join(map(str, random.choices(range(10), k=8)))
    description = f"auto generated_{datetime.date.today().strftime('%B %d, %Y')}"
    mapping[folder_source_id] = AnonymizationParameters(
        patient_name=patient_name, patient_id=patient_id, description=description
    )

    context.get_current_mapping_folder().save_list(mapping)
    click.echo(f"Done. Added '{path}' to mapping")


@click.command()
@pass_map_command_context
@click.argument("selection", type=FileSelectionFileParam())
def add_selection(context: MapCommandContext, selection):
    """Add selection file to mapping
    """
    mapping = get_mapping(context)
    identifier = SourceIdentifierFactory().get_source_identifier_for_obj(selection)
    # make identifier path relative to mapping
    try:
        identifier.identifier = context.get_current_mapping_folder().\
            make_relative(identifier.identifier)
    except MapperException as e:
        raise BadParameter(f"Selection file must be inside mapping folder:{e}")

    # add this selection to mapping
    patient_name = f"autogenerated_{''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}"
    patient_id = "auto_" + "".join(map(str, random.choices(range(10), k=8)))
    description = f"auto generated_{datetime.date.today().strftime('%B %d, %Y')}"

    mapping[identifier] = AnonymizationParameters(
        patient_name=patient_name, patient_id=patient_id, description=description
    )

    context.get_current_mapping_folder().save_list(mapping)
    click.echo(f"Done. Added '{identifier}' to mapping")


@click.command()
@pass_map_command_context
def edit(context: MapCommandContext):
    """Edit the current mapping in OS default editor
    """
    mapping_folder = context.get_current_mapping_folder()
    if mapping_folder.has_mapping_list():
        click.launch(str(mapping_folder.full_path()))
    else:
        click.echo("No mapping file defined in current folder")


for func in [status, init, delete, add_study_folder, edit, add_selection]:
    main.add_command(func)
