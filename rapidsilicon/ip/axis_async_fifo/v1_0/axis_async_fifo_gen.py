#!/usr/bin/env python3
#
# This file is Copyright (c) 2022 RapidSilicon.
#
# SPDX-License-Identifier: MIT

import os
import sys
import argparse

from litex_wrapper.axis_async_fifo_litex_wrapper import AXISASYNCFIFO

from migen import *

from litex.build.generic_platform import *

from litex.build.osfpga import OSFPGAPlatform

from litex.soc.interconnect.axi import AXIStreamInterface

# IOs/Interfaces -----------------------------------------------------------------------------------
def get_clkin_m_ios():
    return [
        ("m_clk", 0, Pins(1)),
        ("m_rst", 0, Pins(1))
    ]
    
def get_clkin_s_ios():
    return [
        ("s_clk", 0, Pins(1)),
        ("s_rst", 0, Pins(1))
    ]
    
def get_slave_status_ios():
    return [
        ("s_status", 0,
            Subsignal("overflow",   Pins(1)),
            Subsignal("bad_frame",  Pins(1)),
            Subsignal("good_frame", Pins(1)),
        )]
    
def get_master_status_ios():
    return [
        ("m_status", 0,
            Subsignal("overflow",   Pins(1)),
            Subsignal("bad_frame",       Pins(1)),
            Subsignal("good_frame",      Pins(1))    
        )
    ]

# AXI_STREAM_FIFO Wrapper ----------------------------------------------------------------------------------
class AXISASYNCFIFOWrapper(Module):
    def __init__(self, platform, depth, data_width, last_en, id_en, id_width, 
                dest_en, dest_width, user_en, user_width, pip_out, out_fifo_en, frame_fifo, bad_frame_value, 
                drop_bad_frame, drop_when_full):

        # Clock Domain
        self.clock_domains.cd_sys = ClockDomain()
        
        # AXI STREAM -------------------------------------------------------------------------------
        s_axis = AXIStreamInterface(
            data_width = data_width,
            user_width = user_width,
            dest_width = dest_width,
            id_width   = id_width,
            keep_width = int((data_width+7)/8)
        )
        
        m_axis = AXIStreamInterface(
            data_width = data_width,
            user_width = user_width,
            dest_width = dest_width,
            id_width   = id_width,
            keep_width = int((data_width+7)/8)
        )
        # Input AXI
        platform.add_extension(s_axis.get_ios("s_axis"))
        self.comb += s_axis.connect_to_pads(platform.request("s_axis"), mode="slave")
        
        # Output AXI
        platform.add_extension(m_axis.get_ios("m_axis"))
        self.comb += m_axis.connect_to_pads(platform.request("m_axis"), mode="master")

        # AXIS-ASYNC-FIFO ----------------------------------------------------------------------------------
        self.submodules.fifo = fifo = AXISASYNCFIFO(platform,
            m_axis          = m_axis,
            s_axis          = s_axis,
            depth           = depth, 
            last_en         = last_en,
            id_en           = id_en,
            dest_en         = dest_en,
            user_en         = user_en,
            pip_out         = pip_out,
            frame_fifo      = frame_fifo,
            out_fifo_en     = out_fifo_en,
            bad_frame_value = bad_frame_value,
            drop_bad_frame  = drop_bad_frame,
            drop_when_full  = drop_when_full
            )
        
        # FIFO Status Signals ----------------------------------------------------------------------
        platform.add_extension(get_slave_status_ios())
        fifo_pads = platform.request("s_status")
        self.comb += [
            fifo_pads.overflow.eq(fifo.s_status_overflow),
            fifo_pads.bad_frame.eq(fifo.s_status_bad_frame),
            fifo_pads.good_frame.eq(fifo.s_status_good_frame),
        ]

        platform.add_extension(get_master_status_ios())
        fifo_pads = platform.request("m_status")
        self.comb += [
            fifo_pads.overflow.eq(fifo.m_status_overflow),
            fifo_pads.bad_frame.eq(fifo.m_status_bad_frame),
            fifo_pads.good_frame.eq(fifo.m_status_good_frame),
        ]

        platform.add_extension(get_clkin_m_ios())
        self.comb += fifo.m_clk.eq(platform.request("m_clk"))
        self.comb += fifo.m_rst.eq(platform.request("m_rst"))
        
        platform.add_extension(get_clkin_s_ios())
        self.comb += fifo.s_clk.eq(platform.request("s_clk"))
        self.comb += fifo.s_rst.eq(platform.request("s_rst"))

# Build --------------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AXIS ASYNC FIFO CORE")

    # Import Common Modules.
    common_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib")
    sys.path.append(common_path)

    from common import IP_Builder

    # Parameter Dependency dictionary
    #                Ports     :    Dependency
    dep_dict = {    
                'id_width'    :   'id_en',
                'dest_width'  :   'dest_en',
                'user_width'  :   'user_en'
    }   

    # IP Builder.
    rs_builder = IP_Builder(device="gemini", ip_name="axis_async_fifo", language="verilog")

    # Core fix value parameters.
    core_fix_param_group = parser.add_argument_group(title="Core fix parameters")
    core_fix_param_group.add_argument("--depth",          type=int,     default=4096,   choices=[8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768],   help="FIFO Depth.")

    # Core bool value parameters.
    core_bool_param_group = parser.add_argument_group(title="Core bool parameters")
    core_bool_param_group.add_argument("--last_en",         type=bool,      default=True,       help="FIFO Last Enable.")
    core_bool_param_group.add_argument("--id_en",           type=bool,      default=True,       help="FIFO ID Enable.")
    core_bool_param_group.add_argument("--dest_en",         type=bool,      default=True,       help="FIFO Destination Enable.")
    core_bool_param_group.add_argument("--user_en",         type=bool,      default=True,       help="FIFO User Enable.")
    core_bool_param_group.add_argument("--pip_out",         type=bool,      default=True,       help="FIFO Pipeline Output.")
    core_bool_param_group.add_argument("--frame_fifo",      type=bool,      default=True,       help="FIFO Frame.")
    core_bool_param_group.add_argument("--out_fifo_en",     type=bool,      default=True,       help="OUTPUT FIFO ENABLE.")
    core_bool_param_group.add_argument("--bad_frame_value", type=bool,      default=True,       help="USER BAD FRAME VALUE.")
    core_bool_param_group.add_argument("--drop_bad_frame",  type=bool,      default=True,       help="FIFO Drop Bad Frame.")
    core_bool_param_group.add_argument("--drop_when_full",  type=bool,      default=True,       help="FIFO Drop Frame When Full.")

    # Core range value parameters.
    core_range_param_group = parser.add_argument_group(title="Core range parameters")
    core_range_param_group.add_argument("--data_width",     type=int,       default=8,      choices=range(1,4097),       help="FIFO Data Width.")
    core_range_param_group.add_argument("--id_width",       type=int,       default=8,      choices=range(1, 33),        help="FIFO ID Width.")
    core_range_param_group.add_argument("--dest_width",     type=int,       default=8,      choices=range(1, 33),        help="FIFO Destination Width.")
    core_range_param_group.add_argument("--user_width",     type=int,       default=1,      choices=range(1, 4097),      help="FIFO User Width.")

    # Build Parameters.
    build_group = parser.add_argument_group(title="Build parameters")
    build_group.add_argument("--build",         action="store_true",                  help="Build Core")
    build_group.add_argument("--build-dir",     default="./",                         help="Build Directory")
    build_group.add_argument("--build-name",    default="axis_async_fifo_wrapper",    help="Build Folder Name, Build RTL File Name and Module Name")

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
    module   = AXISASYNCFIFOWrapper(platform,
        depth          = args.depth,
        data_width     = args.data_width,
        last_en        = args.last_en,
        id_en          = args.id_en,
        id_width       = args.id_width,
        dest_en        = args.dest_en,
        dest_width     = args.dest_width,
        user_en        = args.user_en,
        user_width     = args.user_width,
        pip_out        = args.pip_out,
        frame_fifo     = args.frame_fifo,
        out_fifo_en    = args.out_fifo_en,
        bad_frame_value= args.bad_frame_value,
        drop_bad_frame = args.drop_bad_frame,
        drop_when_full = args.drop_when_full,
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