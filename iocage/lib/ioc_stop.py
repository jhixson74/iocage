"""This stops jails."""
import logging
from subprocess import CalledProcessError, PIPE, Popen, STDOUT, check_call, \
    check_output

from iocage.lib.ioc_json import IOCJson
from iocage.lib.ioc_list import IOCList


class IOCStop(object):
    """Stops a jail and unmounts the jails mountpoints."""

    def __init__(self, uuid, jail, path, conf, silent=False):
        self.pool = IOCJson(" ").json_get_value("pool")
        self.iocroot = IOCJson(self.pool).json_get_value("iocroot")
        self.uuid = uuid
        self.jail = jail
        self.path = path
        self.conf = conf
        self.status, self.jid = IOCList().list_get_jid(uuid)
        self.nics = conf["interfaces"]
        self.lgr = logging.getLogger('ioc_stop')

        if silent:
            self.lgr.disabled = True

        self.__stop_jail__()

    def __stop_jail__(self):
        ip4_addr = self.conf["ip4_addr"]
        vnet = self.conf["vnet"]

        if not self.status:
            self.lgr.error("{} ({}) is not running!".format(self.uuid,
                                                            self.conf["tag"]))
        else:
            self.lgr.info(
                "* Stopping {} ({})".format(self.uuid, self.conf["tag"]))

            if vnet == "on":
                for nic in self.nics.split(","):
                    nic = nic.split(":")[0]
                    try:
                        check_output(["ifconfig", "{}:{}".format(nic, self.jid),
                                      "destroy"], stderr=STDOUT)
                    except CalledProcessError:
                        pass

            if ip4_addr != "inherit" and vnet == "off":
                if ip4_addr != "none":
                    for ip4 in ip4_addr.split():
                        try:
                            iface, addr = ip4.split("/")[0].split("|")
                            check_output(["ifconfig", iface, addr,
                                          "-alias"], stderr=STDOUT)
                        except ValueError:
                            # Likely a misconfigured ip_addr with no interface.
                            self.lgr.error("  ! IP4 address is missing an"
                                           " interface, set ip4_addr to"
                                           " \"INTERFACE|IPADDR\"")
                        except CalledProcessError as err:
                            if "Can't assign requested address" in err.output:
                                # They may have a new address that somehow
                                # didn't set correctly. We shouldn't bail on
                                # that.
                                pass
                            else:
                                raise RuntimeError(
                                    "ERROR: {}".format(err.output.strip()))

            # TODO: Prestop findscript
            exec_stop = self.conf["exec_stop"].split()
            with open("{}/log/{}-console.log".format(self.iocroot,
                                                     self.uuid), "a") as f:
                services = check_call(["jexec",
                                       "ioc-{}".format(self.uuid)] +
                                      exec_stop, stdout=f, stderr=PIPE)
            if services:
                self.lgr.info("  + Stopping services FAILED")
            else:
                self.lgr.info("  + Stopping services OK")

            if self.conf["jail_zfs"] == "on":
                for jdataset in self.conf["jail_zfs_dataset"].split():
                    jdataset = jdataset.strip()
                    children = check_output(["zfs", "list", "-H", "-r", "-o",
                                             "name", "-S", "name",
                                             "{}/{}".format(self.pool,
                                                            jdataset)])

                    for child in children.split():
                        child = child.strip()

                        try:
                            check_output(["jexec", "ioc-{}".format(
                                self.uuid), "zfs", "umount", child],
                                         stderr=STDOUT)
                        except CalledProcessError as err:
                            mountpoint = check_output(["zfs", "get", "-H",
                                                       "-o",
                                                       "value", "mountpoint",
                                                       "{}/{}".format(
                                                           self.pool,
                                                           jdataset)]).strip()
                            if mountpoint == "none":
                                pass
                            else:
                                raise RuntimeError(
                                    "ERROR: {}".format(err.output.strip()))

                    try:
                        check_output(["zfs", "unjail", "ioc-{}".format(
                            self.uuid), "{}/{}".format(self.pool, jdataset)],
                                     stderr=STDOUT)
                    except CalledProcessError as err:
                        raise RuntimeError(
                            "ERROR: {}".format(err.output.strip()))

            stop = check_call(["jail", "-r", "ioc-{}".format(self.uuid)],
                              stderr=PIPE)

            if stop:
                self.lgr.info("  + Removing jail process FAILED")
            else:
                self.lgr.info("  + Removing jail process OK")

            Popen(["umount", "-afF", "{}/fstab".format(self.path)], stderr=PIPE)
            Popen(["umount", "-f", "{}/root/dev/fd".format(self.path)],
                  stderr=PIPE).communicate()
            Popen(["umount", "-f", "{}/root/dev".format(self.path)],
                  stderr=PIPE).communicate()
            Popen(["umount", "-f", "{}/root/proc".format(self.path)],
                  stderr=PIPE).communicate()
            Popen(
                ["umount", "-f", "{}/root/compat/linux/proc".format(self.path)],
                stderr=PIPE).communicate()
