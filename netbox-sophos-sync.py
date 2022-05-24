#!/usr/bin/env python3

import pynetbox
import os
import requests

from config import NB_URL, NB_TOKEN, UTMs, REQUESTS_CA_BUNDLE
from config import DEBUG

api_ethernet = "{}objects/itfhw/ethernet/"
api_lag = "{}objects/itfhw/lag/"
api_lag_params = "{}objects/itfparams/link_aggregation_group/"
api_primary_params = "{}objects/itfparams/primary/"
api_secondary_params = "{}objects/itfparams/secondary/"
api_int_ethernet = "{}objects/interface/ethernet/"
api_int_vlan = "{}objects/interface/vlan/"
api_nodes = "{}nodes/"

os.environ["REQUESTS_CA_BUNDLE"] = REQUESTS_CA_BUNDLE
nb = pynetbox.api(NB_URL, token=NB_TOKEN)


def do_api_call(url):
    r = requests.get(url, verify=False, auth=("token", utm["token"]))
    return r.json()


def update_interfaces(fw_hw_itfs, nb_itfsd, nb_dev):
    for itf in fw_hw_itfs:
        try:
            match = [x for x in nb_itfsd if x["name"] == itf["hardware"]][0]
        except IndexError:
            match = None

        if match:
            nb.dcim.interfaces.update(
                [
                    {
                        "id": match["id"],
                        "device": nb_dev.id,
                        "name": itf["hardware"],
                        # "type": "virtual",
                        "duplex": itf["duplex"],
                        "mac_address": itf["mac"],
                    }
                ]
            )
        else:
            nb.dcim.interfaces.create(
                {
                    "device": nb_dev.id,
                    "name": itf["hardware"],
                    # "type": "virtual",
                    "duplex": itf["duplex"],
                    "mac_address": itf["mac"],
                }
            )


def update_lags(fw_lags, fw_lag_params, nb_itfsd):
    for fw_lag in fw_lags:
        try:
            match = [x for x in nb_itfsd if x["name"] == fw_lag["hardware"]][0]
        except IndexError:
            match = None

        try:
            lag = None
            if fw_lag["hardware"] == "lag0":
                lag = "REF_LagOne"
            elif fw_lag["hardware"] == "lag1":
                lag = "REF_LagTwo"
            elif fw_lag["hardware"] == "lag2":
                lag = "REF_LagThree"
            elif fw_lag["hardware"] == "lag3":
                lag = "REF_LagFour"
            match2 = [x for x in fw_lag_params if x["_ref"] == lag][0]
        except IndexError:
            match2 = None

        if match and match2:
            nb.dcim.interfaces.update(
                [
                    {
                        "id": match["id"],
                        "device": nb_dev.id,
                        "name": fw_lag["hardware"],
                        "mac_address": match2["virtual_mac"],
                        "type": "lag",
                    }
                ]
            )
            pass
        else:
            nb.dcim.interfaces.create(
                {
                    "device": nb_dev.id,
                    "name": fw_lag["hardware"],
                    "type": "lag",
                }
            )


def update_vlan_interfaces():
    pass


for utm in UTMs:
    ### Gather Data
    nodes = do_api_call(api_nodes.format(utm["api-url"]))
    fw_hw_itfs = do_api_call(api_ethernet.format(utm["api-url"]))
    fw_itfs = do_api_call(api_int_ethernet.format(utm["api-url"]))
    fw_vlans = do_api_call(api_int_vlan.format(utm["api-url"]))
    fw_lags = do_api_call(api_lag.format(utm["api-url"]))
    fw_lag_params = do_api_call(api_lag_params.format(utm["api-url"]))
    fw_primary_params = do_api_call(api_primary_params.format(utm["api-url"]))
    fw_secondary_params = do_api_call(api_secondary_params.format(utm["api-url"]))

    fw_node_id = nodes["ha.node_id"]

    nb_chassis = nb.dcim.virtual_chassis.get(name=utm["name"])
    nb_dev = None
    if nb_chassis is None:
        nb_dev = nb.dcim.devices.get(name=utm["name"])
    else:
        if fw_node_id != 1:
            nb_dev = nb.dcim.devices.get(
                vc_position=fw_node_id, virtual_chassis_id=nb_chassis.id
            )
        else:
            nb_dev = nb.dcim.devices.get(nb_chassis.master.id)

    if nb_dev is None:
        raise Exception("No Netbox Device was found.")

    nb_itfs = nb.dcim.interfaces.filter(device_id=nb_dev.id)
    nb_itfsd = []
    for nb_itf in nb_itfs:
        nb_itfsd.append(dict(nb_itf))

    ### Do Stuff
    update_interfaces(fw_hw_itfs, nb_itfsd, nb_dev)
    update_lags(fw_lags, fw_lag_params, nb_itfsd)
    update_vlan_interfaces()
