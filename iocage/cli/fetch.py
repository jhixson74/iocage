"""CLI command to fetch a jail RELEASE."""
from subprocess import check_output

import click

from iocage.lib.ioc_fetch import IOCFetch

__cmdname__ = "fetch_cmd"
__rootcmd__ = True


def validate_count(ctx, param, value):
    """Takes a string, removes the commas and returns an int."""
    try:
        count = value.replace(",", "")
        return int(count)
    except ValueError:
        return int(value)


@click.command(name="fetch", help="Fetch a version of FreeBSD for jail usage.")
@click.option("--http", "-h", default=False,
              help="Have --server define a HTTP server instead.", is_flag=True)
@click.option("--file", "-f", "_file", default=False,
              help="Use a local file directory for root-dir instead of FTP or"
                   " HTTP.", is_flag=True)
@click.option("--server", "-s", default="ftp.freebsd.org",
              help="FTP server to login to.")
@click.option("--user", "-u", default="anonymous", help="The user to use.")
@click.option("--password", "-p", default="anonymous@",
              help="The password to use.")
@click.option("--auth", "-a", default=None, help="Authentication method for "
                                                 "HTTP fetching. Valid "
                                                 "values: basic, digest")
@click.option("--verify/--noverify", default=False, help="Enable or disable"
                                                         " verifying SSL cert"
                                                         " for HTTP fetching.")
@click.option("--release", "-r", help="The FreeBSD release to fetch.")
@click.option("--plugin-file", "-P", help="The plugin file to use.")
@click.option("--plugins", help="List all available plugins for creation.",
              is_flag=True)
@click.argument("props", nargs=-1)
@click.option("--count", "-c", callback=validate_count, default="1")
@click.option("--root-dir", "-d", help="Root directory " +
                                       "containing all the RELEASEs.")
def fetch_cmd(http, _file, server, user, password, auth, verify, release,
              plugins, plugin_file, root_dir, props, count):
    """CLI command that calls fetch_release()"""
    freebsd_version = check_output(["freebsd-version"])

    if "HBSD" in freebsd_version:
        if server == "ftp.freebsd.org":
            hardened = True
    else:
        hardened = False

    if plugins or plugin_file:
        ip = [x for x in props if x.startswith("ip4_addr")]
        if not ip:
            raise RuntimeError("IP address is needed to fetch a plugin!\n"
                               "Please specify "
                               "ip4_addr=\"INTERFACE|IPADDRESS\"!")
        if plugins:
            IOCFetch("").fetch_plugin_index(props)
            exit()

        if count == 1:
            IOCFetch("", server, user, password, auth, root_dir,
                     http=http, _file=_file, verify=verify,
                     hardened=hardened).fetch_plugin(plugin_file, props, 0)
        else:
            for j in xrange(1, count + 1):
                IOCFetch("", server, user, password, auth, root_dir,
                         http=http, _file=_file, verify=verify,
                         hardened=hardened).fetch_plugin(plugin_file, props, j)
    else:
        IOCFetch(release, server, user, password, auth, root_dir, http=http,
                 _file=_file, verify=verify, hardened=hardened).fetch_release()
