// Copyright 2018 ETH Zurich and University of Bologna.
// Copyright and related rights are licensed under the Solderpad Hardware
// License, Version 0.51 (the "License"); you may not use this file except in
// compliance with the License.  You may obtain a copy of the License at
// http://solderpad.org/licenses/SHL-0.51. Unless required by applicable law
// or agreed to in writing, software, hardware and materials distributed under
// this License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
// CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

////////////////////////////////////////////////////////////////////////////////
// Engineer:       Renzo Andri - andrire@student.ethz.ch                      //
//                                                                            //
// Additional contributions by:                                               //
//                 Igor Loi - igor.loi@unibo.it                               //
//                 Andreas Traber - atraber@student.ethz.ch                   //
//                 Sven Stucki - svstucki@student.ethz.ch                     //
//                                                                            //
// Design Name:    Instruction Fetch Stage                                    //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Instruction fetch unit: Selection of the next PC, and      //
//                 buffering (sampling) of the read instruction               //
//                                                                            //
/////////////////////////////////////////////////////////////////////////////////



import cv32e40p_pkg::*;
import cv32e40p_pkg2::*;




module cv32e40p_if_stage
#(
        parameter PULP_XPULP          = 0,
        parameter PULP_OBI            = 0,
        parameter PULP_SECURE         = 0,
        parameter FPU                 = 0
)
(
        input  logic                    clk ,
        input  logic                    rst_n ,
        input  logic            [23:0]  m_trap_base_addr_i ,
        input  logic            [23:0]  u_trap_base_addr_i ,
        input  logic             [1:0]  trap_addr_mux_i ,
        input  logic            [31:0]  boot_addr_i ,
        input  logic            [31:0]  dm_exception_addr_i ,
        input  logic            [31:0]  dm_halt_addr_i ,
        input  logic                    req_i ,
        input  logic                    instr_gnt_i ,
        input  logic                    instr_rvalid_i ,
        input  logic            [31:0]  instr_rdata_i ,
        input  logic                    instr_err_i ,
        input  logic                    instr_err_pmp_i ,
        input  logic                    clear_instr_valid_i ,
        input  logic                    pc_set_i ,
        input  logic            [31:0]  mepc_i ,
        input  logic            [31:0]  uepc_i ,
        input  logic            [31:0]  depc_i ,
        input  logic             [3:0]  pc_mux_i ,
        input  logic             [2:0]  exc_pc_mux_i ,
        input  logic             [4:0]  m_exc_vec_pc_mux_i ,
        input  logic             [4:0]  u_exc_vec_pc_mux_i ,
        input  logic            [31:0]  jump_target_id_i ,
        input  logic            [31:0]  jump_target_ex_i ,
        input  logic                    hwlp_jump_i ,
        input  logic            [31:0]  hwlp_target_i ,
        input  logic                    halt_if_i ,
        input  logic                    id_ready_i ,
        output logic                    instr_req_o ,
        output logic            [31:0]  instr_addr_o ,
        output logic                    instr_valid_id_o ,
        output logic            [31:0]  instr_rdata_id_o ,
        output logic                    is_compressed_id_o ,
        output logic                    illegal_c_insn_id_o ,
        output logic            [31:0]  pc_if_o ,
        output logic            [31:0]  pc_id_o ,
        output logic                    is_fetch_failed_o ,
        output logic                    csr_mtvec_init_o ,
        output logic                    if_busy_o ,
        output logic                    perf_imiss_o 
);
        logic [2:0]                   if_valid_tr;
        logic [2:0]                   if_ready_tr;
        logic [2:0]                   prefetch_busy_tr;
        logic [2:0]                   branch_req_tr;
        logic [2:0]          [31:0]   branch_addr_n_tr;
        logic [2:0]                   fetch_valid_tr;
        logic [2:0]                   fetch_ready_tr;
        logic [2:0]          [31:0]   fetch_rdata_tr;
        logic [2:0]          [31:0]   exc_pc_tr;
        logic [2:0]          [23:0]   trap_base_addr_tr;
        logic [2:0]           [4:0]   exc_vec_pc_mux_tr;
        logic [2:0]                   fetch_failed_tr;
        logic [2:0]                   aligner_ready_tr;
        logic [2:0]                   instr_valid_tr;
        logic [2:0]                   illegal_c_insn_tr;
        logic [2:0]          [31:0]   instr_aligned_tr;
        logic [2:0]          [31:0]   instr_decompressed_tr;
        logic [2:0]                   instr_compressed_int_tr;

        logic [2:0]                   instr_req_o_tr;
        logic [2:0]          [31:0]   instr_addr_o_tr;
        logic [2:0]                   instr_valid_id_o_tr;
        logic [2:0]          [31:0]   instr_rdata_id_o_tr;
        logic [2:0]                   is_compressed_id_o_tr;
        logic [2:0]                   illegal_c_insn_id_o_tr;
        logic [2:0]          [31:0]   pc_if_o_tr;
        logic [2:0]          [31:0]   pc_id_o_tr;
        logic [2:0]                   is_fetch_failed_o_tr;
        logic [2:0]                   csr_mtvec_init_o_tr;
        logic [2:0]                   perf_imiss_o_tr;

        assign instr_req_o = instr_req_o_tr[0];
        assign instr_addr_o = instr_addr_o_tr[0];
        assign instr_valid_id_o = instr_valid_id_o_tr[0];
        assign instr_rdata_id_o = instr_rdata_id_o_tr[0];
        assign is_compressed_id_o = is_compressed_id_o_tr[0];
        assign illegal_c_insn_id_o = illegal_c_insn_id_o_tr[0];
        assign pc_if_o = pc_if_o_tr[0];
        assign pc_id_o = pc_id_o_tr[0];
        assign is_fetch_failed_o = is_fetch_failed_o_tr[0];
        assign csr_mtvec_init_o = csr_mtvec_init_o_tr[0];
        assign perf_imiss_o = perf_imiss_o_tr[0];

        logic [5:0]           [2:0]   is_broken_o_ft;
        logic [5:0]                   err_detected_o_ft;
        logic [5:0]                   err_corrected_o_ft;

        logic [5:0]           [2:0]   set_broken_i_ft;
        assign set_broken_i_ft = {3'b0, 3'b0, 3'b0, 3'b0, 3'b0, 3'b0};

        assign if_busy_o = prefetch_busy_tr[0];

        assign fetch_failed_tr = {1'b0, 1'b0, 1'b0};



        ///////////////////////////////////////////////////////////

        cv32e40p_program_counter_definition_ft program_counter_definition_ft
        (
                // Input ports of program_counter_definition_ft
                .m_exc_vec_pc_mux_i     (  { m_exc_vec_pc_mux_i  , m_exc_vec_pc_mux_i  , m_exc_vec_pc_mux_i  } ),
                .u_exc_vec_pc_mux_i     (  { u_exc_vec_pc_mux_i  , u_exc_vec_pc_mux_i  , u_exc_vec_pc_mux_i  } ),
                .trap_addr_mux_i        (  { trap_addr_mux_i  , trap_addr_mux_i  , trap_addr_mux_i  } ),
                .exc_pc_mux_i           (  { exc_pc_mux_i  , exc_pc_mux_i  , exc_pc_mux_i  } ),
                .dm_halt_addr_i         (  { dm_halt_addr_i  , dm_halt_addr_i  , dm_halt_addr_i  } ),
                .m_trap_base_addr_i     (  { m_trap_base_addr_i  , m_trap_base_addr_i  , m_trap_base_addr_i  } ),
                .u_trap_base_addr_i     (  { u_trap_base_addr_i  , u_trap_base_addr_i  , u_trap_base_addr_i  } ),
                .boot_addr_i            (  { boot_addr_i  , boot_addr_i  , boot_addr_i  } ),
                .dm_exception_addr_i    (  { dm_exception_addr_i  , dm_exception_addr_i  , dm_exception_addr_i  } ),
                .jump_target_id_i       (  { jump_target_id_i  , jump_target_id_i  , jump_target_id_i  } ),
                .jump_target_ex_i       (  { jump_target_ex_i  , jump_target_ex_i  , jump_target_ex_i  } ),
                .mepc_i                 (  { mepc_i  , mepc_i  , mepc_i  }  ),
                .uepc_i                 (  { uepc_i  , uepc_i  , uepc_i  }  ),
                .depc_i                 (  { depc_i  , depc_i  , depc_i  }  ),
                .pc_id_o                (  pc_id_o_tr                       ),
                .hwlp_target_i          (  { hwlp_target_i  , hwlp_target_i  , hwlp_target_i  } ),
                .pc_set_i               (  { pc_set_i  , pc_set_i  , pc_set_i  } ),
                .pc_mux_i               (  { pc_mux_i  , pc_mux_i  , pc_mux_i  } ),

                // Input diff ports of program_counter_definition_ft
                .clk                    (  clk                              ),
                .rst_n                  (  rst_n                            ),
                .set_broken_i           (  set_broken_i_ft[CVIFST_PRCODEFT] ),

                // Output ports of program_counter_definition_ft
                .branch_addr_n          (  branch_addr_n_tr                 ),
                .csr_mtvec_init_o       (  csr_mtvec_init_o_tr              ),

                // Output diff ports of program_counter_definition_ft
                .is_broken_o            (  is_broken_o_ft[CVIFST_PRCODEFT]  ),
                .err_detected_o         (  err_detected_o_ft[CVIFST_PRCODEFT] ),
                .err_corrected_o        (  err_corrected_o_ft[CVIFST_PRCODEFT] )
        );



        // prefetch buffer, caches a fixed number of instructions
        
        cv32e40p_prefetch_buffer_ft
        #( 
                 .PULP_OBI            (  PULP_OBI            ),
                 .PULP_XPULP          (  PULP_XPULP          ) 
        )
         prefetch_buffer_ft
        (
                // Input ports of prefetch_buffer_ft
                .req_i                  (  { req_i  , req_i  , req_i  }     ),
                .branch_i               (  branch_req_tr                    ),
                .branch_addr_i          (  { {branch_addr_n_tr[2][31:1], 1'b0}  , {branch_addr_n_tr[1][31:1], 1'b0}  , {branch_addr_n_tr[0][31:1], 1'b0}  } ),
                .hwlp_jump_i            (  { hwlp_jump_i  , hwlp_jump_i  , hwlp_jump_i  } ),
                .hwlp_target_i          (  { hwlp_target_i  , hwlp_target_i  , hwlp_target_i  } ),
                .fetch_ready_i          (  fetch_ready_tr                   ),
                .instr_gnt_i            (  { instr_gnt_i  , instr_gnt_i  , instr_gnt_i  } ),
                .instr_rdata_i          (  { instr_rdata_i  , instr_rdata_i  , instr_rdata_i  } ),
                .instr_rvalid_i         (  { instr_rvalid_i  , instr_rvalid_i  , instr_rvalid_i  } ),
                .instr_err_i            (  { instr_err_i  , instr_err_i  , instr_err_i  } ),
                .instr_err_pmp_i        (  { instr_err_pmp_i  , instr_err_pmp_i  , instr_err_pmp_i  } ),
                .clk                    (  clk                              ),
                .rst_n                  (  rst_n                            ),

                // Input diff ports of prefetch_buffer_ft
                .set_broken_i           (  set_broken_i_ft[CVIFST_PRBUFT]   ),

                // Output ports of prefetch_buffer_ft
                .fetch_valid_o          (  fetch_valid_tr                   ),
                .fetch_rdata_o          (  fetch_rdata_tr                   ),
                .instr_req_o            (  instr_req_o_tr                   ),
                .instr_addr_o           (  instr_addr_o_tr                  ),
                .busy_o                 (  prefetch_busy_tr                 ),

                // Output diff ports of prefetch_buffer_ft
                .is_broken_o            (  is_broken_o_ft[CVIFST_PRBUFT]    ),
                .err_detected_o         (  err_detected_o_ft[CVIFST_PRBUFT] ),
                .err_corrected_o        (  err_corrected_o_ft[CVIFST_PRBUFT] )
        );



        cv32e40p_if_stage_fsm_logic_ft if_stage_fsm_logic_ft
        (
                // Input ports of if_stage_fsm_logic_ft
                .pc_set_i               (  { pc_set_i  , pc_set_i  , pc_set_i  } ),
                .fetch_valid            (  fetch_valid_tr                   ),
                .req_i                  (  { req_i  , req_i  , req_i  }     ),
                .if_valid               (  if_valid_tr                      ),
                .aligner_ready          (  aligner_ready_tr                 ),

                // Input diff ports of if_stage_fsm_logic_ft
                .clk                    (  clk                              ),
                .rst_n                  (  rst_n                            ),
                .set_broken_i           (  set_broken_i_ft[CVIFST_IFSTFSLOFT] ),

                // Output ports of if_stage_fsm_logic_ft
                .branch_req             (  branch_req_tr                    ),
                .fetch_ready            (  fetch_ready_tr                   ),
                .perf_imiss_o           (  perf_imiss_o_tr                  ),

                // Output diff ports of if_stage_fsm_logic_ft
                .is_broken_o            (  is_broken_o_ft[CVIFST_IFSTFSLOFT] ),
                .err_detected_o         (  err_detected_o_ft[CVIFST_IFSTFSLOFT] ),
                .err_corrected_o        (  err_corrected_o_ft[CVIFST_IFSTFSLOFT] )
        );



        cv32e40p_if_pipeline_ft if_pipeline_ft
        (
                // Input ports of if_pipeline_ft
                .instr_decompressed     (  instr_decompressed_tr            ),
                .instr_compressed_int   (  instr_compressed_int_tr          ),
                .pc_if_o                (  pc_if_o_tr                       ),
                .fetch_failed           (  fetch_failed_tr                  ),
                .id_ready_i             (  { id_ready_i  , id_ready_i  , id_ready_i  } ),
                .halt_if_i              (  { halt_if_i  , halt_if_i  , halt_if_i  } ),
                .instr_valid            (  instr_valid_tr                   ),
                .clear_instr_valid_i    (  { clear_instr_valid_i  , clear_instr_valid_i  , clear_instr_valid_i  } ),
                .illegal_c_insn         (  illegal_c_insn_tr                ),
                .fetch_valid            (  fetch_valid_tr                   ),
                .clk                    (  clk                              ),
                .rst_n                  (  rst_n                            ),

                // Input diff ports of if_pipeline_ft
                .set_broken_i           (  set_broken_i_ft[CVIFST_IFPIFT]   ),

                // Output ports of if_pipeline_ft
                .instr_valid_id_o       (  instr_valid_id_o_tr              ),
                .instr_rdata_id_o       (  instr_rdata_id_o_tr              ),
                .is_fetch_failed_o      (  is_fetch_failed_o_tr             ),
                .pc_id_o                (  pc_id_o_tr                       ),
                .is_compressed_id_o     (  is_compressed_id_o_tr            ),
                .illegal_c_insn_id_o    (  illegal_c_insn_id_o_tr           ),
                .if_valid               (  if_valid_tr                      ),

                // Output diff ports of if_pipeline_ft
                .is_broken_o            (  is_broken_o_ft[CVIFST_IFPIFT]    ),
                .err_detected_o         (  err_detected_o_ft[CVIFST_IFPIFT] ),
                .err_corrected_o        (  err_corrected_o_ft[CVIFST_IFPIFT] )
        );



        cv32e40p_aligner_ft aligner_ft
        (
                // Input ports of aligner_ft
                .fetch_valid_i          (  fetch_valid_tr                   ),
                .if_valid_i             (  if_valid_tr                      ),
                .fetch_rdata_i          (  fetch_rdata_tr                   ),
                .branch_addr_i          (  { {branch_addr_n_tr[2][31:1], 1'b0}  , {branch_addr_n_tr[1][31:1], 1'b0}  , {branch_addr_n_tr[0][31:1], 1'b0}  } ),
                .branch_i               (  branch_req_tr                    ),
                .hwlp_addr_i            (  { hwlp_target_i  , hwlp_target_i  , hwlp_target_i  } ),
                .hwlp_update_pc_i       (  { hwlp_jump_i  , hwlp_jump_i  , hwlp_jump_i  } ),
                .clk                    (  clk                              ),
                .rst_n                  (  rst_n                            ),

                // Input diff ports of aligner_ft
                .set_broken_i           (  set_broken_i_ft[CVIFST_ALFT]     ),

                // Output ports of aligner_ft
                .aligner_ready_o        (  aligner_ready_tr                 ),
                .instr_aligned_o        (  instr_aligned_tr                 ),
                .instr_valid_o          (  instr_valid_tr                   ),
                .pc_o                   (  pc_if_o_tr                       ),

                // Output diff ports of aligner_ft
                .is_broken_o            (  is_broken_o_ft[CVIFST_ALFT]      ),
                .err_detected_o         (  err_detected_o_ft[CVIFST_ALFT]   ),
                .err_corrected_o        (  err_corrected_o_ft[CVIFST_ALFT]  )
        );


        cv32e40p_compressed_decoder_ft
        #( 
                 .FPU                 (  FPU                 ) 
        )
         compressed_decoder_ft
        (
                // Input ports of compressed_decoder_ft
                .instr_i                (  instr_aligned_tr                 ),

                // Input diff ports of compressed_decoder_ft
                .clk                    (  clk                              ),
                .rst_n                  (  rst_n                            ),
                .set_broken_i           (  set_broken_i_ft[CVIFST_CODEFT]   ),

                // Output ports of compressed_decoder_ft
                .instr_o                (  instr_decompressed_tr            ),
                .is_compressed_o        (  instr_compressed_int_tr          ),
                .illegal_instr_o        (  illegal_c_insn_tr                ),

                // Output diff ports of compressed_decoder_ft
                .is_broken_o            (  is_broken_o_ft[CVIFST_CODEFT]    ),
                .err_detected_o         (  err_detected_o_ft[CVIFST_CODEFT] ),
                .err_corrected_o        (  err_corrected_o_ft[CVIFST_CODEFT] )
        );


        //----------------------------------------------------------------------------
        // Assertions
        //----------------------------------------------------------------------------

`ifdef CV32E40P_ASSERT_ON

  generate
  if (!PULP_XPULP) begin

    // Check that PC Mux cannot select Hardware Loop address iF PULP extensions are not included
    property p_pc_mux_0;
       @(posedge clk) disable iff (!rst_n) (1'b1) |-> (pc_mux_i != PC_HWLOOP);
    endproperty

    a_pc_mux_0 : assert property(p_pc_mux_0);

  end
  endgenerate

 generate
  if (!PULP_SECURE) begin

    // Check that PC Mux cannot select URET address if User Mode is not included
    property p_pc_mux_1;
       @(posedge clk) disable iff (!rst_n) (1'b1) |-> (pc_mux_i != PC_URET);
    endproperty

    a_pc_mux_1 : assert property(p_pc_mux_1);

  end
  endgenerate

`endif
endmodule
