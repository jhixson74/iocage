"""This is responsible for getting a jail property."""
import json
import logging

import click
from texttable import Texttable

from iocage.lib.ioc_json import IOCJson
from iocage.lib.ioc_list import IOCList

__cmdname__ = "get_cmd"


@click.command(context_settings=dict(
    max_content_width=400, ), name="get", help="Gets the specified property.")
@click.argument("prop")
@click.argument("jail", required=True, default="")
@click.option("--header", "-h", "-H", is_flag=True, default=True,
              help="For scripting, use tabs for separators.")
@click.option("--recursive", "-r", help="Get the specified property for all " +
                                        "jails.", flag_value="recursive")
@click.option("--plugin", "-P",
              help="Get the specified key for a plugin jail, if accessing a"
                   " nested key use . as a separator."
                   "\n\b Example: iocage get -P foo.bar.baz PLUGIN",
              is_flag=True)
def get_cmd(prop, jail, recursive, header, plugin):
    """Get a list of jails and print the property."""
    lgr = logging.getLogger('ioc_cli_get')

    get_jid = IOCList.list_get_jid
    jails, paths = IOCList("uuid").list_datasets()
    jail_list = []
    table = Texttable(max_width=0)

    if recursive is None:
        if jail == "":
            lgr.info("Usage: iocage get [OPTIONS] PROP JAIL\n")
            raise RuntimeError("Error: Missing argument \"jail\".")

        _jail = {tag: uuid for (tag, uuid) in jails.iteritems() if
                 uuid.startswith(jail) or tag == jail}

        if len(_jail) == 1:
            tag, uuid = next(_jail.iteritems())
            path = paths[tag]
        elif len(_jail) > 1:
            lgr.error("Multiple jails found for"
                      " {}:".format(jail))
            for t, u in sorted(_jail.iteritems()):
                lgr.error("  {} ({})".format(u, t))
            raise RuntimeError()
        else:
            raise RuntimeError("{} not found!".format(jail))

        if prop == "state":
            status, _ = get_jid(path.split("/")[3])

            if status:
                state = "up"
            else:
                state = "down"

            lgr.info(state)
        elif plugin:
            _prop = prop.split(".")
            props = IOCJson(path).json_plugin_get_value(_prop)

            if isinstance(props, dict):
                lgr.info(json.dumps(props, indent=4))
            else:
                pass
        elif prop == "all":
            props = IOCJson(path).json_get_value(prop)

            for p, v in props.iteritems():
                lgr.info("{}:{}".format(p, v))
        else:
            try:
                lgr.info(IOCJson(path).json_get_value(prop))
            except:
                raise RuntimeError("{} is not a valid property!".format(prop))
    else:
        for j in jails:
            uuid = jails[j]
            path = paths[j]
            try:
                if prop == "state":
                    status, _ = get_jid(path.split("/")[3])

                    if status:
                        state = "up"
                    else:
                        state = "down"

                    jail_list.append([j, state])
                elif prop == "all":
                    raise
                else:
                    jail_list.append(
                        [uuid, j, IOCJson(path).json_get_value(prop)])
            except:
                raise RuntimeError("{} is not a valid property!".format(prop))

        # Prints the table
        if header:
            jail_list.insert(0, ["UUID", "TAG", "PROP - {}".format(prop)])
            table.add_rows(jail_list)
            lgr.info(table.draw())
        else:
            for jail in jail_list:
                lgr.info("\t".join(jail))
