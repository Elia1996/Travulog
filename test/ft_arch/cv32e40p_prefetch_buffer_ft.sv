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

module cv32e40p_prefetch_buffer_ft
#(
        parameter PULP_OBI            = 0,
        parameter PULP_XPULP          = 1
)
(

        // compressed decoder input output
        input logic [2:0]                   req_i,
        input logic [2:0]                   branch_i,
        input logic [2:0]          [31:0]   branch_addr_i,
        input logic [2:0]                   hwlp_jump_i,
        input logic [2:0]          [31:0]   hwlp_target_i,
        input logic [2:0]                   fetch_ready_i,
        input logic [2:0]                   instr_gnt_i,
        input logic [2:0]          [31:0]   instr_rdata_i,
        input logic [2:0]                   instr_rvalid_i,
        input logic [2:0]                   instr_err_i,
        input logic [2:0]                   instr_err_pmp_i,
        output logic [2:0]                   fetch_valid_o,
        output logic [2:0]          [31:0]   fetch_rdata_o,
        output logic [2:0]                   instr_req_o,
        output logic [2:0]          [31:0]   instr_addr_o,
        output logic [2:0]                   busy_o,

        input logic clk,
        input logic rst_n,                

        // fault tolerant state
        input logic [2:0] set_broken_i,
        output logic [2:0] is_broken_o,
        output logic err_detected_o,
        output logic err_corrected_o
);
        // Signals out to each compressed decoder block to be voted
        logic [2:0]                   fetch_valid_o_to_vote ;
        logic [2:0]          [31:0]   fetch_rdata_o_to_vote ;
        logic [2:0]                   instr_req_o_to_vote ;
        logic [2:0]          [31:0]   instr_addr_o_to_vote ;
        logic [2:0]                   busy_o_to_vote ;

        // Error signals
        logic [2:0] fetch_valid_o_block_err ;
        logic [2:0] fetch_rdata_o_block_err ;
        logic [2:0] instr_req_o_block_err ;
        logic [2:0] instr_addr_o_block_err ;
        logic [2:0] busy_o_block_err ;

        // Signals that use error signal to find if there is one error on
        // each block, it is the or of previous signals
        logic [2:0] block_err_detected;
        logic [2:0] err_detected;
        logic [2:0] err_corrected;

        // variable for generate cycle
        generate
                case (PRBU_FT)
                        0 : begin
                                cv32e40p_prefetch_buffer
                                #( 
                                         .PULP_OBI            (  PULP_OBI            ),
                                         .PULP_XPULP          (  PULP_XPULP          ) 
                                )
                                 prefetch_buffer_no_ft
                                (
                                        // Input ports of prefetch_buffer_no_ft
                                        .clk                    (  clk                              ),
                                        .rst_n                  (  rst_n                            ),
                                        .req_i                  (  req_i[0]                         ),
                                        .branch_i               (  branch_i[0]                      ),
                                        .branch_addr_i          (  branch_addr_i[0]                 ),
                                        .hwlp_jump_i            (  hwlp_jump_i[0]                   ),
                                        .hwlp_target_i          (  hwlp_target_i[0]                 ),
                                        .fetch_ready_i          (  fetch_ready_i[0]                 ),
                                        .instr_gnt_i            (  instr_gnt_i[0]                   ),
                                        .instr_rdata_i          (  instr_rdata_i[0]                 ),
                                        .instr_rvalid_i         (  instr_rvalid_i[0]                ),
                                        .instr_err_i            (  instr_err_i[0]                   ),
                                        .instr_err_pmp_i        (  instr_err_pmp_i[0]               ),

                                        // Output ports of prefetch_buffer_no_ft
                                        .fetch_valid_o          (  fetch_valid_o[0]                 ),
                                        .fetch_rdata_o          (  fetch_rdata_o[0]                 ),
                                        .instr_req_o            (  instr_req_o[0]                   ),
                                        .instr_addr_o           (  instr_addr_o[0]                  ),
                                        .busy_o                 (  busy_o[0]                        )
                                );
                                // error
                                assign block_err_detected = {1'b0,1'b0,1'b0};
                        end
                        default : begin
                                // Input case 
                                case (PRBU_TIN) 
                                        0 : begin // Single input
                                                genvar i;
                                                for (i=0; i<3; i=i+1)  begin 
                                                        cv32e40p_prefetch_buffer
                                                        #( 
                                                                 .PULP_OBI            (  PULP_OBI            ),
                                                                 .PULP_XPULP          (  PULP_XPULP          ) 
                                                        )
                                                         prefetch_buffer_single_input
                                                        (
                                                                // Input ports of prefetch_buffer_single_input
                                                                .clk                    (  clk                              ),
                                                                .rst_n                  (  rst_n                            ),
                                                                .req_i                  (  req_i[0]                         ),
                                                                .branch_i               (  branch_i[0]                      ),
                                                                .branch_addr_i          (  branch_addr_i[0]                 ),
                                                                .hwlp_jump_i            (  hwlp_jump_i[0]                   ),
                                                                .hwlp_target_i          (  hwlp_target_i[0]                 ),
                                                                .fetch_ready_i          (  fetch_ready_i[0]                 ),
                                                                .instr_gnt_i            (  instr_gnt_i[0]                   ),
                                                                .instr_rdata_i          (  instr_rdata_i[0]                 ),
                                                                .instr_rvalid_i         (  instr_rvalid_i[0]                ),
                                                                .instr_err_i            (  instr_err_i[0]                   ),
                                                                .instr_err_pmp_i        (  instr_err_pmp_i[0]               ),

                                                                // Output ports of prefetch_buffer_single_input
                                                                .fetch_valid_o          (  fetch_valid_o_to_vote[i]         ),
                                                                .fetch_rdata_o          (  fetch_rdata_o_to_vote[i]         ),
                                                                .instr_req_o            (  instr_req_o_to_vote[i]           ),
                                                                .instr_addr_o           (  instr_addr_o_to_vote[i]          ),
                                                                .busy_o                 (  busy_o_to_vote[i]                )
                                                        );
                                        end
                                        default : begin // Triplicated input
                                                genvar i;
                                                for (i=0; i<3; i=i+1)  begin 
                                                        cv32e40p_prefetch_buffer
                                                        #( 
                                                                 .PULP_OBI            (  PULP_OBI            ),
                                                                 .PULP_XPULP          (  PULP_XPULP          ) 
                                                        )
                                                         prefetch_buffer_tiple_input
                                                        (
                                                                // Input ports of prefetch_buffer_tiple_input
                                                                .clk                    (  clk                              ),
                                                                .rst_n                  (  rst_n                            ),
                                                                .req_i                  (  req_i[i]                         ),
                                                                .branch_i               (  branch_i[i]                      ),
                                                                .branch_addr_i          (  branch_addr_i[i]                 ),
                                                                .hwlp_jump_i            (  hwlp_jump_i[i]                   ),
                                                                .hwlp_target_i          (  hwlp_target_i[i]                 ),
                                                                .fetch_ready_i          (  fetch_ready_i[i]                 ),
                                                                .instr_gnt_i            (  instr_gnt_i[i]                   ),
                                                                .instr_rdata_i          (  instr_rdata_i[i]                 ),
                                                                .instr_rvalid_i         (  instr_rvalid_i[i]                ),
                                                                .instr_err_i            (  instr_err_i[i]                   ),
                                                                .instr_err_pmp_i        (  instr_err_pmp_i[i]               ),

                                                                // Output ports of prefetch_buffer_tiple_input
                                                                .fetch_valid_o          (  fetch_valid_o_to_vote[i]         ),
                                                                .fetch_rdata_o          (  fetch_rdata_o_to_vote[i]         ),
                                                                .instr_req_o            (  instr_req_o_to_vote[i]           ),
                                                                .instr_addr_o           (  instr_addr_o_to_vote[i]          ),
                                                                .busy_o                 (  busy_o_to_vote[i]                )
                                                        );
                                        end
                                endcase        

                                 // Voter for TOVOTE signal, triple voter if
                                 // PRBU_TOUT[0] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(PRBU_TOUT[0])
                                 ) voter_fetch_valid_o_0
                                 (
                                          .to_vote_i( fetch_valid_o_to_vote ),
                                          .voted_o( fetch_valid_o),
                                          .block_err_o( fetch_valid_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[0]),
                                          .err_corrected_o(err_corrected[0])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // PRBU_TOUT[1] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(32),
                                          .TOUT(PRBU_TOUT[1])
                                 ) voter_fetch_rdata_o_1
                                 (
                                          .to_vote_i( fetch_rdata_o_to_vote ),
                                          .voted_o( fetch_rdata_o),
                                          .block_err_o( fetch_rdata_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[1]),
                                          .err_corrected_o(err_corrected[1])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // PRBU_TOUT[2] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(PRBU_TOUT[2])
                                 ) voter_instr_req_o_2
                                 (
                                          .to_vote_i( instr_req_o_to_vote ),
                                          .voted_o( instr_req_o),
                                          .block_err_o( instr_req_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[2]),
                                          .err_corrected_o(err_corrected[2])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // PRBU_TOUT[3] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(32),
                                          .TOUT(PRBU_TOUT[3])
                                 ) voter_instr_addr_o_3
                                 (
                                          .to_vote_i( instr_addr_o_to_vote ),
                                          .voted_o( instr_addr_o),
                                          .block_err_o( instr_addr_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[3]),
                                          .err_corrected_o(err_corrected[3])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // PRBU_TOUT[4] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(PRBU_TOUT[4])
                                 ) voter_busy_o_4
                                 (
                                          .to_vote_i( busy_o_to_vote ),
                                          .voted_o( busy_o),
                                          .block_err_o( busy_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[4]),
                                          .err_corrected_o(err_corrected[4])
                                 );
                                 
                                assign err_detected_o =  err_detected[0]
                                                       | err_detected[1]
                                                       | err_detected[2];
                                assign err_corrected_o =  err_corrected[0]
                                                        | err_corrected[1]
                                                        | err_corrected[2];
                                
                                assign block_err_detected[0] =  fetch_valid_o_block_err[0]
                                | fetch_rdata_o_block_err[0]
                                | instr_req_o_block_err[0]
                                | instr_addr_o_block_err[0]
                                | busy_o_block_err[0]; 
                                assign block_err_detected[1] =  fetch_valid_o_block_err[1]
                                | fetch_rdata_o_block_err[1]
                                | instr_req_o_block_err[1]
                                | instr_addr_o_block_err[1]
                                | busy_o_block_err[1]; 
                                assign block_err_detected[2] =  fetch_valid_o_block_err[2]
                                | fetch_rdata_o_block_err[2]
                                | instr_req_o_block_err[2]
                                | instr_addr_o_block_err[2]
                                | busy_o_block_err[2]; 
                                        
                                genvar m;
                                for (m=0;  m<3 ; m=m+1) begin 
                                        // This block is a counter that is incremented each
                                        // time there is an error and decremented when it
                                        // there is not. The value returned is is_broken_o
                                        // , if it is one the block is broken and should't be
                                        // used
                                        cv32e40p_breakage_monitor
                                        #(
                                                .DECREMENT(PRBU_DECREMENT),
                                                .INCREMENT(PRBU_INCREMENT),
                                                .BREAKING_THRESHOLD(PRBU_BREAKING_THRESHOLD),
                                                .COUNT_BIT(PRBU_COUNT_BIT),
                                                .INC_DEC_BIT(PRBU_INC_DEC_BIT)
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

