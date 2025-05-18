from typing import Optional
import socket
import fcntl
import struct

def routefmt_to_strfmt(route_addr: str) -> str:
    h2d = lambda x: str(int(x, 16))
    ret = (h2d(route_addr[6:8]) + "." +
           h2d(route_addr[4:6]) + "." +
           h2d(route_addr[2:4]) + "." +
           h2d(route_addr[0:2]))
    return ret

def get_default_interface() -> Optional[str]:
    def_iface = None
    def_gw = None
    min_metric = None
    with open("/proc/net/route", "rt") as f_route:
        for i, line in enumerate(f_route.readlines()):
            if i == 0:
                continue

            fields = line.split()
            cur_iface = fields[0]
            cur_destination = fields[1]
            cur_gw = fields[2]
            cur_metric = int(fields[6])
            if cur_destination == "00000000" and (min_metric is None or
                                                  cur_metric < min_metric):
                def_iface = cur_iface
                def_gw = cur_gw
                min_metric = cur_metric
    return def_iface, routefmt_to_strfmt(def_gw) if def_gw is not None else ""

def get_ip_addr(interface_name: str, def_gw: str) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((def_gw, 80)) # port doesn't matter since we do not exchange data
    ret = s.getsockname()[0]
    s.close() # do not leave dangling file descriptors
    return ret

def get_default_ip() -> str:
    default_interface, default_gw = get_default_interface()
    if default_interface is None:
        return ""
    return get_ip_addr(default_interface, default_gw)
