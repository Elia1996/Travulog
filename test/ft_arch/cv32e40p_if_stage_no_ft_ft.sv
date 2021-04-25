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
////////////////////////////////////////////////////////////////////////////////

module cv32e40p_if_stage_ft
#(
        parameter PULP_XPULP          = 0,
        parameter PULP_OBI            = 0,
        parameter PULP_SECURE         = 0,
        parameter FPU                 = 0
)
(
        input  logic                    clk ,
        input  logic                    rst_n ,
        input  logic    [2:0]   [23:0]  m_trap_base_addr_i ,
        input  logic    [2:0]   [23:0]  u_trap_base_addr_i ,
        input  logic    [2:0]    [1:0]  trap_addr_mux_i ,
        input  logic    [2:0]   [31:0]  boot_addr_i ,
        input  logic    [2:0]   [31:0]  dm_exception_addr_i ,
        input  logic    [2:0]   [31:0]  dm_halt_addr_i ,
        input  logic    [2:0]           req_i ,
        input  logic    [2:0]           instr_gnt_i ,
        input  logic    [2:0]           instr_rvalid_i ,
        input  logic    [2:0]   [31:0]  instr_rdata_i ,
        input  logic    [2:0]           instr_err_i ,
        input  logic    [2:0]           instr_err_pmp_i ,
        input  logic    [2:0]           clear_instr_valid_i ,
        input  logic    [2:0]           pc_set_i ,
        input  logic    [2:0]   [31:0]  mepc_i ,
        input  logic    [2:0]   [31:0]  uepc_i ,
        input  logic    [2:0]   [31:0]  depc_i ,
        input  logic    [2:0]    [3:0]  pc_mux_i ,
        input  logic    [2:0]    [2:0]  exc_pc_mux_i ,
        input  logic    [2:0]    [4:0]  m_exc_vec_pc_mux_i ,
        input  logic    [2:0]    [4:0]  u_exc_vec_pc_mux_i ,
        input  logic    [2:0]   [31:0]  jump_target_id_i ,
        input  logic    [2:0]   [31:0]  jump_target_ex_i ,
        input  logic    [2:0]           hwlp_jump_i ,
        input  logic    [2:0]   [31:0]  hwlp_target_i ,
        input  logic    [2:0]           halt_if_i ,
        input  logic    [2:0]           id_ready_i ,
        output logic    [2:0]           instr_req_o ,
        output logic    [2:0]   [31:0]  instr_addr_o ,
        output logic    [2:0]           instr_valid_id_o ,
        output logic    [2:0]   [31:0]  instr_rdata_id_o ,
        output logic    [2:0]           is_compressed_id_o ,
        output logic    [2:0]           illegal_c_insn_id_o ,
        output logic    [2:0]   [31:0]  pc_if_o ,
        output logic    [2:0]   [31:0]  pc_id_o ,
        output logic    [2:0]           is_fetch_failed_o ,
        output logic    [2:0]           csr_mtvec_init_o ,
        output logic    [2:0]           if_busy_o ,
        output logic    [2:0]           perf_imiss_o 
)
        logic    [2:0]   [31:0]  branch_addr_n ;
        logic    [5:0]    [2:0]  set_broken_i ;
        logic    [5:0]    [2:0]  is_broken_o ;
        logic    [5:0]           err_detected_o ;
        logic    [5:0]           err_corrected_o ;
        logic             [2:0]  branch_req ;
        logic             [2:0]  fetch_ready ;
        logic             [2:0]  fetch_valid ;
        logic    [2:0]   [31:0]  fetch_rdata ;
        logic             [2:0]  prefetch_busy ;
        logic             [2:0]  if_valid ;
        logic             [2:0]  aligner_ready ;
        logic    [2:0]   [31:0]  instr_decompressed ;
        logic             [2:0]  instr_compressed_int ;
        logic             [2:0]  fetch_failed ;
        logic             [2:0]  instr_valid ;
        logic             [2:0]  illegal_c_insn ;
        logic    [2:0]   [31:0]  instr_aligned ;


        // exception PC selection mux
        cv32e40p_program_counter_definition_ft program_counter_definition_ft
        (
                // Input ports of program_counter_definition_ft
                .m_exc_vec_pc_mux_i     (  m_exc_vec_pc_mux_i               ),
                .u_exc_vec_pc_mux_i     (  u_exc_vec_pc_mux_i               ),
                .trap_addr_mux_i        (  trap_addr_mux_i                  ),
                .exc_pc_mux_i           (  exc_pc_mux_i                     ),
                .dm_halt_addr_i         (  dm_halt_addr_i                   ),
                .m_trap_base_addr_i     (  m_trap_base_addr_i               ),
                .u_trap_base_addr_i     (  u_trap_base_addr_i               ),
                .boot_addr_i            (  boot_addr_i                      ),
                .dm_exception_addr_i    (  dm_exception_addr_i              ),
                .jump_target_id_i       (  jump_target_id_i                 ),
                .jump_target_ex_i       (  jump_target_ex_i                 ),
                .mepc_i                 (  mepc_i                           ),
                .uepc_i                 (  uepc_i                           ),
                .depc_i                 (  depc_i                           ),
                .pc_id_o                (  pc_id_o                          ),
                .hwlp_target_i          (  hwlp_target_i                    ),
                .pc_set_i               (  pc_set_i                         ),
                .pc_mux_i               (  pc_mux_i                         ),

                // Input diff ports of program_counter_definition_ft
                .clk                    (  clk                              ),
                .rst_n                  (  rst_n                            ),
                .set_broken_i           (  set_broken_i[IFST_PRCODE_I]      ),

                // Output ports of program_counter_definition_ft
                .branch_addr_n          (  branch_addr_n                    ),
                .csr_mtvec_init_o       (  csr_mtvec_init_o                 ),

                // Output diff ports of program_counter_definition_ft
                .is_broken_o            (  is_broken_o[IFST_PRCODE_I]       ),
                .err_detected_o         (  err_detected_o[IFST_PRCODE_I]    ),
                .err_corrected_o        (  err_corrected_o[IFST_PRCODE_I]   )
        );

        assign fetch_failed    = 1'b0; // PMP is not supported in CV32E40P

        // prefetch buffer, caches a fixed number of instructions
        //
        cv32e40p_prefetch_buffer_ft
        #( 
                 .PULP_OBI            (  PULP_OBI            ),
                 .PULP_XPULP          (  PULP_XPULP          ) 
        )
         prefetch_buffer_ft
        (
                // Input ports of prefetch_buffer_ft
                .req_i                  (  req_i                            ),
                .branch_i               (  branch_req                       ),
                .branch_addr_i          (  { {branch_addr_n[0][31:1], 1'b0}, {branch_addr_n[1][31:1], 1'b0}, {branch_addr_n[2][31:1], 1'b0}}  ),
                .hwlp_jump_i            (  hwlp_jump_i                      ),
                .hwlp_target_i          (  hwlp_target_i                    ),
                .fetch_ready_i          (  fetch_ready                      ),
                .instr_gnt_i            (  instr_gnt_i                      ),
                .instr_rdata_i          (  instr_rdata_i                    ),
                .instr_rvalid_i         (  instr_rvalid_i                   ),
                .instr_err_i            (  instr_err_i                      ),
                .instr_err_pmp_i        (  instr_err_pmp_i                  ),
                .clk                    (  clk                              ),
                .rst_n                  (  rst_n                            ),

                // Input diff ports of prefetch_buffer_ft
                .set_broken_i           (  set_broken_i[IFST_PRBU_I]        ),

                // Output ports of prefetch_buffer_ft
                .fetch_valid_o          (  fetch_valid                      ),
                .fetch_rdata_o          (  fetch_rdata                      ),
                .instr_req_o            (  instr_req_o                      ),
                .instr_addr_o           (  instr_addr_o                     ),
                .busy_o                 (  prefetch_busy                    ),

                // Output diff ports of prefetch_buffer_ft
                .is_broken_o            (  is_broken_o[IFST_PRBU_I]         ),
                .err_detected_o         (  err_detected_o[IFST_PRBU_I]      ),
                .err_corrected_o        (  err_corrected_o[IFST_PRBU_I]     )
        );


        cv32e40p_if_stage_fsm_ft if_stage_fsm_ft
        (
                // Input ports of if_stage_fsm_ft
                .pc_set_i               (  pc_set_i                         ),
                .fetch_valid            (  fetch_valid                      ),
                .req_i                  (  req_i                            ),
                .if_valid               (  if_valid                         ),
                .aligner_ready          (  aligner_ready                    ),

                // Input diff ports of if_stage_fsm_ft
                .clk                    (  clk                              ),
                .rst_n                  (  rst_n                            ),
                .set_broken_i           (  set_broken_i[IFST_IFSTFS_I]      ),

                // Output ports of if_stage_fsm_ft
                .branch_req             (  branch_req                       ),
                .fetch_ready            (  fetch_ready                      ),
                .perf_imiss_o           (  perf_imiss_o                     ),

                // Output diff ports of if_stage_fsm_ft
                .is_broken_o            (  is_broken_o[IFST_IFSTFS_I]       ),
                .err_detected_o         (  err_detected_o[IFST_IFSTFS_I]    ),
                .err_corrected_o        (  err_corrected_o[IFST_IFSTFS_I]   )
        );

        assign if_busy_o       = prefetch_busy;

        cv32e40p_if_pipeline_ft if_pipeline_ft
        (
                // Input ports of if_pipeline_ft
                .instr_decompressed     (  instr_decompressed               ),
                .instr_compressed_int   (  instr_compressed_int             ),
                .pc_if_o                (  pc_if_o                          ),
                .fetch_failed           (  fetch_failed                     ),
                .id_ready_i             (  id_ready_i                       ),
                .halt_if_i              (  halt_if_i                        ),
                .instr_valid            (  instr_valid                      ),
                .clear_instr_valid_i    (  clear_instr_valid_i              ),
                .illegal_c_insn         (  illegal_c_insn                   ),
                .fetch_valid            (  fetch_valid                      ),
                .clk                    (  clk                              ),
                .rst_n                  (  rst_n                            ),

                // Input diff ports of if_pipeline_ft
                .set_broken_i           (  set_broken_i[IFST_IFPI_I]        ),

                // Output ports of if_pipeline_ft
                .instr_valid_id_o       (  instr_valid_id_o                 ),
                .instr_rdata_id_o       (  instr_rdata_id_o                 ),
                .is_fetch_failed_o      (  is_fetch_failed_o                ),
                .pc_id_o                (  pc_id_o                          ),
                .is_compressed_id_o     (  is_compressed_id_o               ),
                .illegal_c_insn_id_o    (  illegal_c_insn_id_o              ),
                .if_valid               (  if_valid                         ),

                // Output diff ports of if_pipeline_ft
                .is_broken_o            (  is_broken_o[IFST_IFPI_I]         ),
                .err_detected_o         (  err_detected_o[IFST_IFPI_I]      ),
                .err_corrected_o        (  err_corrected_o[IFST_IFPI_I]     )
        );


        cv32e40p_aligner_ft aligner_ft
        (
                // Input ports of aligner_ft
                .fetch_valid_i          (  fetch_valid                      ),
                .if_valid_i             (  if_valid                         ),
                .fetch_rdata_i          (  fetch_rdata                      ),
                .branch_addr_i          (  { {branch_addr_n[0][31:1], 1'b0}, {branch_addr_n[1][31:1], 1'b0}, {branch_addr_n[2][31:1], 1'b0}}  ),
                .branch_i               (  branch_req                       ),
                .hwlp_addr_i            (  hwlp_target_i                    ),
                .hwlp_update_pc_i       (  hwlp_jump_i                      ),
                .clk                    (  clk                              ),
                .rst_n                  (  rst_n                            ),

                // Input diff ports of aligner_ft
                .set_broken_i           (  set_broken_i[IFST_AL_I]          ),

                // Output ports of aligner_ft
                .aligner_ready_o        (  aligner_ready                    ),
                .instr_aligned_o        (  { instr_aligned[0][0], instr_aligned[1][0], instr_aligned[2][0]}  ),
                .instr_valid_o          (  instr_valid                      ),
                .pc_o                   (  pc_if_o                          ),

                // Output diff ports of aligner_ft
                .is_broken_o            (  is_broken_o[IFST_AL_I]           ),
                .err_detected_o         (  err_detected_o[IFST_AL_I]        ),
                .err_corrected_o        (  err_corrected_o[IFST_AL_I]       )
        );

        cv32e40p_compressed_decoder_ft
        #( 
                 .FPU                 (  FPU                 ) 
        )
         compressed_decoder_ft
        (
                // Input ports of compressed_decoder_ft
                .instr_i                (  instr_aligned                    ),

                // Input diff ports of compressed_decoder_ft
                .clk                    (  clk                              ),
                .rst_n                  (  rst_n                            ),
                .set_broken_i           (  set_broken_i[IFST_CODE_I]        ),

                // Output ports of compressed_decoder_ft
                .instr_o                (  instr_decompressed               ),
                .is_compressed_o        (  instr_compressed_int             ),
                .illegal_instr_o        (  illegal_c_insn                   ),

                // Output diff ports of compressed_decoder_ft
                .is_broken_o            (  is_broken_o[IFST_CODE_I]         ),
                .err_detected_o         (  err_detected_o[IFST_CODE_I]      ),
                .err_corrected_o        (  err_corrected_o[IFST_CODE_I]     )
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

