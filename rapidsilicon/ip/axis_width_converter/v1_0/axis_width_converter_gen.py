#!/usr/bin/env python3
#
# This file is Copyright (c) 2022 RapidSilicon.
#
# SPDX-License-Identifier: MIT

import os
import sys
import logging
import argparse

from migen import *

from litex.build.generic_platform import *

from litex.build.osfpga import OSFPGAPlatform 

from litex.soc.interconnect import stream

from litex.soc.interconnect.axi import *

# IOs/Interfaces -----------------------------------------------------------------------------------
def get_clkin_ios():
    return [
        ("axis_clk",  0, Pins(1)),
        ("axis_rst",  0, Pins(1)),
    ]

# AXI Stream Converter -----------------------------------------------------------------------------
class AXISConverter(Module):
    def __init__(self, platform, in_width=64, out_width=64, user_width=0, reverse=False):
        # Clocking ---------------------------------------------------------------------------------
        platform.add_extension(get_clkin_ios())
        self.clock_domains.cd_sys  = ClockDomain()
        self.comb += self.cd_sys.clk.eq(platform.request("axis_clk"))
        self.comb += self.cd_sys.rst.eq(platform.request("axis_rst"))

        # Input AXI --------------------------------------------------------------------------------
        axis_in = AXIStreamInterface(data_width=in_width, user_width=user_width)
        platform.add_extension(axis_in.get_ios("s_axis"))
        self.comb += axis_in.connect_to_pads(platform.request("s_axis"), mode="slave")

        # Output AXI -------------------------------------------------------------------------------
        axis_out = AXIStreamInterface(data_width=out_width, user_width=user_width)
        platform.add_extension(axis_out.get_ios("m_axis"))
        self.comb += axis_out.connect_to_pads(platform.request("m_axis"), mode="master")

        # Converter --------------------------------------------------------------------------------
        converter = stream.StrideConverter(axis_in.description, axis_out.description, reverse=reverse)
        self.submodules += converter
        self.comb += axis_in.connect(converter.sink)
        self.comb += converter.source.connect(axis_out)

# Build --------------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AXI STREAM CONVERTER CORE")

    # Import Common Modules.
    common_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib")
    sys.path.append(common_path)

    from common import IP_Builder

    # Parameter Dependency dictionary
    #                Ports         :    Dependency
    dep_dict = {}            

    # IP Builder.
    rs_builder = IP_Builder(device="gemini", ip_name="axis_width_converter", language="verilog")

    logging.info("===================================================")
    logging.info("IP    : %s", rs_builder.ip_name.upper())
    logging.info(("==================================================="))
    
    # Core fix value parameters.
    core_fix_param_group = parser.add_argument_group(title="Core fix parameters")
    core_fix_param_group.add_argument("--core_in_width",    type=int,   default=128,    choices=[8, 16, 32, 64, 128, 256, 512, 1024],   help="AXI-ST Input Data-width.")
    core_fix_param_group.add_argument("--core_out_width",   type=int,   default=64,     choices=[8, 16, 32, 64, 128, 256, 512, 1024],   help="AXI-ST Output Data-width.")

    # Core bool value parameters.
    core_bool_param_group = parser.add_argument_group(title="Core bool parameters")
    core_bool_param_group.add_argument("--core_reverse",    type=bool,      default=False,       help="Reverse Converter Ordering.")

    # Core range value parameters.
    core_range_param_group = parser.add_argument_group(title="Core range parameters")
    core_range_param_group.add_argument("--core_user_width",    type=int,       default=1,      choices=range(1,4097),      help="AXI-ST User width.")


    # Build Parameters.
    build_group = parser.add_argument_group(title="Build parameters")
    build_group.add_argument("--build",             action="store_true",                    help="Build core.")
    build_group.add_argument("--build-dir",         default="./",                           help="Build directory.")
    build_group.add_argument("--build-name",        default="axis_width_converter",         help="Build Folder Name, Build RTL File Name and Module Name")

    # JSON Import/Template
    json_group = parser.add_argument_group(title="JSON parameters")
    json_group.add_argument("--json",                                               help="Generate core from JSON file.")
    json_group.add_argument("--json-template",      action="store_true",            help="Generate JSON template.")

    args = parser.parse_args()

    # Import JSON (Optional) -----------------------------------------------------------------------
    if args.json:
        args = rs_builder.import_args_from_json(parser=parser, json_filename=args.json)

    # Export JSON Template (Optional) --------------------------------------------------------------
    if args.json_template:
        rs_builder.export_json_template(parser=parser, dep_dict=dep_dict)

    # Create LiteX Core ----------------------------------------------------------------------------
    core_in_width   = int(args.core_in_width)
    core_out_width  = int(args.core_out_width)
    core_user_width = int(args.core_user_width)
    platform   = OSFPGAPlatform(io=[], toolchain="raptor", device="gemini")
    module     = AXISConverter(platform,
        in_width   = core_in_width,
        out_width  = core_out_width,
        user_width = core_user_width,
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
