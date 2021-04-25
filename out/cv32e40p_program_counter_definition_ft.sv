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
// Engineer:       Elia Ribaldone  - ribaldoneelia@gmail.com                  //
//                                                                            //
// Additional contributions by:                                               //
//                  Marcello Neri - s257090@studenti.polito.it                //
//                   Luca Fiore - luca.fiore@studenti.polito.it               //
// Design Name:    Compressed instruction decoder fault tolerant              //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Decodes RISC-V compressed instructions into their RV32     //
//                 equivalent. This module is fully combinatorial.            //
//                 Float extensions added                                     //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

import cv32e40p_pkg2_ft::*;
import cv32e40p_pkg::*;

module cv32e40p_program_counter_definition_ft
(

        // compressed decoder input output
        input logic [2:0]           [4:0]   m_exc_vec_pc_mux_i,
        input logic [2:0]           [4:0]   u_exc_vec_pc_mux_i,
        input logic [2:0]           [1:0]   trap_addr_mux_i,
        input logic [2:0]           [2:0]   exc_pc_mux_i,
        input logic [2:0]          [31:0]   dm_halt_addr_i,
        input logic [2:0]          [23:0]   m_trap_base_addr_i,
        input logic [2:0]          [23:0]   u_trap_base_addr_i,
        input logic [2:0]          [31:0]   boot_addr_i,
        input logic [2:0]          [31:0]   dm_exception_addr_i,
        input logic [2:0]          [31:0]   jump_target_id_i,
        input logic [2:0]          [31:0]   jump_target_ex_i,
        input logic [2:0]          [31:0]   mepc_i,
        input logic [2:0]          [31:0]   uepc_i,
        input logic [2:0]          [31:0]   depc_i,
        input logic [2:0]          [31:0]   pc_id_o,
        input logic [2:0]          [31:0]   hwlp_target_i,
        input logic [2:0]                   pc_set_i,
        input logic [2:0]           [3:0]   pc_mux_i,
        output logic [2:0]          [31:0]   branch_addr_n,
        output logic [2:0]                   csr_mtvec_init_o,

        input logic clk,
        input logic rst_n,                

        // fault tolerant state
        input logic [2:0] set_broken_i,
        output logic [2:0] is_broken_o,
        output logic err_detected_o,
        output logic err_corrected_o
);
        // Signals out to each compressed decoder block to be voted
        logic [2:0]          [31:0]   branch_addr_n_to_vote ;
        logic [2:0]                   csr_mtvec_init_o_to_vote ;

        // Error signals
        logic [2:0] branch_addr_n_block_err ;
        logic [2:0] csr_mtvec_init_o_block_err ;

        // Signals that use error signal to find if there is one error on
        // each block, it is the or of previous signals
        logic [2:0] block_err_detected;
        logic [1:0] err_detected;
        logic [1:0] err_corrected;

        // variable for generate cycle
        generate
                case (PRCODE_FT)
                        0 : begin
                                cv32e40p_program_counter_definition program_counter_definition_no_ft
                                (
                                        // Input ports of program_counter_definition_no_ft
                                        .m_exc_vec_pc_mux_i     (  m_exc_vec_pc_mux_i[0]            ),
                                        .u_exc_vec_pc_mux_i     (  u_exc_vec_pc_mux_i[0]            ),
                                        .trap_addr_mux_i        (  trap_addr_mux_i[0]               ),
                                        .exc_pc_mux_i           (  exc_pc_mux_i[0]                  ),
                                        .dm_halt_addr_i         (  dm_halt_addr_i[0]                ),
                                        .m_trap_base_addr_i     (  m_trap_base_addr_i[0]            ),
                                        .u_trap_base_addr_i     (  u_trap_base_addr_i[0]            ),
                                        .boot_addr_i            (  boot_addr_i[0]                   ),
                                        .dm_exception_addr_i    (  dm_exception_addr_i[0]           ),
                                        .jump_target_id_i       (  jump_target_id_i[0]              ),
                                        .jump_target_ex_i       (  jump_target_ex_i[0]              ),
                                        .mepc_i                 (  mepc_i[0]                        ),
                                        .uepc_i                 (  uepc_i[0]                        ),
                                        .depc_i                 (  depc_i[0]                        ),
                                        .pc_id_o                (  pc_id_o[0]                       ),
                                        .hwlp_target_i          (  hwlp_target_i[0]                 ),
                                        .pc_set_i               (  pc_set_i[0]                      ),
                                        .pc_mux_i               (  pc_mux_i[0]                      ),

                                        // Output ports of program_counter_definition_no_ft
                                        .branch_addr_n          (  branch_addr_n[0]                 ),
                                        .csr_mtvec_init_o       (  csr_mtvec_init_o[0]              )
                                );
                                // Since we don't use FT can't be detected an
                                // error
                                assign block_err_detected = {1'b0,1'b0,1'b0};
                        end
                        default : begin
                                // Input case 
                                case (PRCODE_TIN) 
                                        0 : begin // Single input
                                                genvar i;
                                                for (i=0; i<3; i=i+1)  begin 
                                                        cv32e40p_program_counter_definition program_counter_definition_single_input
                                                        (
                                                                // Input ports of program_counter_definition_single_input
                                                                .m_exc_vec_pc_mux_i     (  m_exc_vec_pc_mux_i[0]            ),
                                                                .u_exc_vec_pc_mux_i     (  u_exc_vec_pc_mux_i[0]            ),
                                                                .trap_addr_mux_i        (  trap_addr_mux_i[0]               ),
                                                                .exc_pc_mux_i           (  exc_pc_mux_i[0]                  ),
                                                                .dm_halt_addr_i         (  dm_halt_addr_i[0]                ),
                                                                .m_trap_base_addr_i     (  m_trap_base_addr_i[0]            ),
                                                                .u_trap_base_addr_i     (  u_trap_base_addr_i[0]            ),
                                                                .boot_addr_i            (  boot_addr_i[0]                   ),
                                                                .dm_exception_addr_i    (  dm_exception_addr_i[0]           ),
                                                                .jump_target_id_i       (  jump_target_id_i[0]              ),
                                                                .jump_target_ex_i       (  jump_target_ex_i[0]              ),
                                                                .mepc_i                 (  mepc_i[0]                        ),
                                                                .uepc_i                 (  uepc_i[0]                        ),
                                                                .depc_i                 (  depc_i[0]                        ),
                                                                .pc_id_o                (  pc_id_o[0]                       ),
                                                                .hwlp_target_i          (  hwlp_target_i[0]                 ),
                                                                .pc_set_i               (  pc_set_i[0]                      ),
                                                                .pc_mux_i               (  pc_mux_i[0]                      ),

                                                                // Output ports of program_counter_definition_single_input
                                                                .branch_addr_n          (  branch_addr_n_to_vote[i]         ),
                                                                .csr_mtvec_init_o       (  csr_mtvec_init_o_to_vote[i]      )
                                                        );
                                                end                                                
                                        end
                                        default : begin // Triplicated input
                                                genvar i;
                                                for (i=0; i<3; i=i+1)  begin 
                                                        cv32e40p_program_counter_definition program_counter_definition_tiple_input
                                                        (
                                                                // Input ports of program_counter_definition_tiple_input
                                                                .m_exc_vec_pc_mux_i     (  m_exc_vec_pc_mux_i[i]            ),
                                                                .u_exc_vec_pc_mux_i     (  u_exc_vec_pc_mux_i[i]            ),
                                                                .trap_addr_mux_i        (  trap_addr_mux_i[i]               ),
                                                                .exc_pc_mux_i           (  exc_pc_mux_i[i]                  ),
                                                                .dm_halt_addr_i         (  dm_halt_addr_i[i]                ),
                                                                .m_trap_base_addr_i     (  m_trap_base_addr_i[i]            ),
                                                                .u_trap_base_addr_i     (  u_trap_base_addr_i[i]            ),
                                                                .boot_addr_i            (  boot_addr_i[i]                   ),
                                                                .dm_exception_addr_i    (  dm_exception_addr_i[i]           ),
                                                                .jump_target_id_i       (  jump_target_id_i[i]              ),
                                                                .jump_target_ex_i       (  jump_target_ex_i[i]              ),
                                                                .mepc_i                 (  mepc_i[i]                        ),
                                                                .uepc_i                 (  uepc_i[i]                        ),
                                                                .depc_i                 (  depc_i[i]                        ),
                                                                .pc_id_o                (  pc_id_o[i]                       ),
                                                                .hwlp_target_i          (  hwlp_target_i[i]                 ),
                                                                .pc_set_i               (  pc_set_i[i]                      ),
                                                                .pc_mux_i               (  pc_mux_i[i]                      ),

                                                                // Output ports of program_counter_definition_tiple_input
                                                                .branch_addr_n          (  branch_addr_n_to_vote[i]         ),
                                                                .csr_mtvec_init_o       (  csr_mtvec_init_o_to_vote[i]      )
                                                        );
                                                end        
                                        end
                                endcase        

                                 // Voter for TOVOTE signal, triple voter if
                                 // PRCODE_TOUT[0] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(32),
                                          .TOUT(PRCODE_TOUT[0])
                                 ) voter_branch_addr_n_0
                                 (
                                          .to_vote_i( branch_addr_n_to_vote ),
                                          .voted_o( branch_addr_n),
                                          .block_err_o( branch_addr_n_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[0]),
                                          .err_corrected_o(err_corrected[0])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // PRCODE_TOUT[1] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(PRCODE_TOUT[1])
                                 ) voter_csr_mtvec_init_o_1
                                 (
                                          .to_vote_i( csr_mtvec_init_o_to_vote ),
                                          .voted_o( csr_mtvec_init_o),
                                          .block_err_o( csr_mtvec_init_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[1]),
                                          .err_corrected_o(err_corrected[1])
                                 );
                                 
                                
                                assign err_detected_o =  err_detected[0]| err_detected[1]; 
                                assign err_corrected_o =  err_corrected[0]| err_corrected[1]; 
                                
                                assign block_err_detected[0] =  branch_addr_n_block_err[0]
                                                              | csr_mtvec_init_o_block_err[0]; 
                                assign block_err_detected[1] =  branch_addr_n_block_err[1]
                                                              | csr_mtvec_init_o_block_err[1]; 
                                assign block_err_detected[2] =  branch_addr_n_block_err[2]
                                                              | csr_mtvec_init_o_block_err[2]; 
                                        
                                genvar m;
                                for (m=0;  m<3 ; m=m+1) begin 
                                        // This block is a counter that is incremented each
                                        // time there is an error and decremented when it
                                        // there is not. The value returned is is_broken_o
                                        // , if it is one the block is broken and should't be
                                        // used
                                        cv32e40p_breakage_monitor
                                        #(
                                                .DECREMENT(PRCODE_DECREMENT),
                                                .INCREMENT(PRCODE_INCREMENT),
                                                .BREAKING_THRESHOLD(PRCODE_BREAKING_THRESHOLD),
                                                .COUNT_BIT(PRCODE_COUNT_BIT),
                                                .INC_DEC_BIT(PRCODE_INC_DEC_BIT)
                                        ) breakage_monitor
                                        (
                                                .rst_n(rst_n),
                                                .clk(clk),
                                                .err_detected_i(block_err_detected[m]),
                                                .set_broken_i(set_broken_i[m]),
                                                .is_broken_o(is_broken_o[m])
                                        );        
                                        // We find is the block have an error.
                                end

                        end
                endcase        

        endgenerate

endmodule

