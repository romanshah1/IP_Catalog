#!/usr/bin/env python3
#
# This file is Copyright (c) 2022 RapidSilicon.
#
# SPDX-License-Identifier: MIT

import os
import sys
import logging
import argparse

from litex_wrapper.axil_crossbar_litex_wrapper import AXILITECROSSBAR

from migen import *

from litex.build.generic_platform import *

from litex.build.osfpga import OSFPGAPlatform

from litex.soc.interconnect.axi import AXILiteInterface


# IOs/Interfaces -----------------------------------------------------------------------------------
def get_clkin_ios():
    return [
        ("clk",  0, Pins(1)),
        ("rst",  0, Pins(1)),
    ]

# AXI LITE CROSSBAR ----------------------------------------------------------------------------------
class AXILITECROSSBARWrapper(Module):
    def __init__(self, platform, s_count, m_count, data_width, addr_width):
        # Clocking ---------------------------------------------------------------------------------
        platform.add_extension(get_clkin_ios())
        self.clock_domains.cd_sys  = ClockDomain()
        self.comb += self.cd_sys.clk.eq(platform.request("clk"))
        self.comb += self.cd_sys.rst.eq(platform.request("rst"))

        # Slave Interfaces
        s_axils = []
        for s_count in range(s_count):
            s_axil = AXILiteInterface(data_width = data_width , address_width = addr_width)
            if s_count>9:
                platform.add_extension(s_axil.get_ios("s{}_axil".format(s_count)))
                self.comb += s_axil.connect_to_pads(platform.request("s{}_axil".format(s_count)), mode="slave")
            else:
                platform.add_extension(s_axil.get_ios("s0{}_axil".format(s_count)))
                self.comb += s_axil.connect_to_pads(platform.request("s0{}_axil".format(s_count)), mode="slave")
                
            s_axils.append(s_axil)
        
        # Master Interfaces
        m_axils = []    
        for m_count in range(m_count):
            m_axil = AXILiteInterface(data_width = data_width , address_width = addr_width)
            if m_count>9:
                platform.add_extension(m_axil.get_ios("m{}_axil".format(m_count)))
                self.comb += m_axil.connect_to_pads(platform.request("m{}_axil".format(m_count)), mode="master")
            else:
                platform.add_extension(m_axil.get_ios("m0{}_axil".format(m_count)))
                self.comb += m_axil.connect_to_pads(platform.request("m0{}_axil".format(m_count)), mode="master")
            
            m_axils.append(m_axil)

        # AXIL-CROSSBAR ----------------------------------------------------------------------------------
        self.submodules += AXILITECROSSBAR (platform, 
            s_axil      = s_axils,
            m_axil      = m_axils,
            s_count     = s_count,
            m_count     = m_count
            )

# Build --------------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AXI_LITE_CROSSBAR_CORE")

    # Import Common Modules.
    common_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib")
    sys.path.append(common_path)

    from common import IP_Builder

    # Parameter Dependency dictionary
    dep_dict = {}            

    # IP Builder.
    rs_builder = IP_Builder(device="gemini", ip_name="axil_crossbar", language="verilog")

    logging.info("===================================================")
    logging.info("IP    : %s", rs_builder.ip_name.upper())
    logging.info(("==================================================="))
    
    # Core fix value parameters.
    core_fix_param_group = parser.add_argument_group(title="Core fix parameters")
    core_fix_param_group.add_argument("--data_width",     default=32,   choices=[32, 64],  type=int,   help="Crossbar Data Width.")
    core_fix_param_group.add_argument("--addr_width",     default=32,   choices=[32, 64, 128, 256],         type=int,   help="Crossbar Address Width.")

    # Core range value parameters.
    core_range_param_group = parser.add_argument_group(title="Core range parameters")
    core_range_param_group.add_argument("--m_count",      default=4,    choices=range(1,17),     type=int,   help="Crossbar Master Interfaces.")
    core_range_param_group.add_argument("--s_count",      default=4,    choices=range(1,17),     type=int,   help="Crossbar Slave Interfaces.")
    
    # Build Parameters.
    build_group = parser.add_argument_group(title="Build parameters")
    build_group.add_argument("--build",         action="store_true",                    help="Build Core")
    build_group.add_argument("--build-dir",     default="./",                           help="Build Directory")
    build_group.add_argument("--build-name",    default="axil_crossbar_wrapper",        help="Build Folder Name, Build RTL File Name and Module Name")

    # JSON Import/Template
    json_group = parser.add_argument_group(title="JSON Parameters")
    json_group.add_argument("--json",                                           help="Generate Core from JSON File")
    json_group.add_argument("--json-template",  action="store_true",            help="Generate JSON Template")

    args = parser.parse_args()
    
    # Import JSON (Optional) -----------------------------------------------------------------------
    if args.json:
        args = rs_builder.import_args_from_json(parser=parser, json_filename=args.json)

    # Export JSON Template (Optional) --------------------------------------------------------------
    if args.json_template:
        rs_builder.export_json_template(parser=parser, dep_dict=dep_dict)

    # Create Wrapper -------------------------------------------------------------------------------
    platform = OSFPGAPlatform(io=[], toolchain="raptor", device="gemini")
    module     = AXILITECROSSBARWrapper(platform,
        m_count    = args.m_count,
        s_count    = args.s_count,
        data_width = args.data_width,
        addr_width = args.addr_width,
    )

    # Build Project --------------------------------------------------------------------------------
    if args.build:
        rs_builder.prepare(
            build_dir  = args.build_dir,
            build_name = args.build_name,
            version    = "v1_0"
        )
        rs_builder.copy_files(gen_path=os.path.dirname(__file__))
        rs_builder.generate_tcl()
        rs_builder.generate_wrapper(
            platform   = platform,
            module     = module,
        )

if __name__ == "__main__":
    main()
