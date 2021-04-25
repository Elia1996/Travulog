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

module cv32e40p_aligner_ft
(

        // compressed decoder input output
        input logic [2:0]                   fetch_valid_i,
        input logic [2:0]                   if_valid_i,
        input logic [2:0]          [31:0]   fetch_rdata_i,
        input logic [2:0]          [31:0]   branch_addr_i,
        input logic [2:0]                   branch_i,
        input logic [2:0]          [31:0]   hwlp_addr_i,
        input logic [2:0]                   hwlp_update_pc_i,
        output logic [2:0]                   aligner_ready_o,
        output logic [2:0]          [31:0]   instr_aligned_o,
        output logic [2:0]                   instr_valid_o,
        output logic [2:0]          [31:0]   pc_o,

        input logic clk,
        input logic rst_n,                

        // fault tolerant state
        input logic [2:0] set_broken_i,
        output logic [2:0] is_broken_o,
        output logic err_detected_o,
        output logic err_corrected_o
);
        // Signals out to each compressed decoder block to be voted
        logic [2:0]                   aligner_ready_o_to_vote ;
        logic [2:0]          [31:0]   instr_aligned_o_to_vote ;
        logic [2:0]                   instr_valid_o_to_vote ;
        logic [2:0]          [31:0]   pc_o_to_vote ;

        // Error signals
        logic [2:0] aligner_ready_o_block_err ;
        logic [2:0] instr_aligned_o_block_err ;
        logic [2:0] instr_valid_o_block_err ;
        logic [2:0] pc_o_block_err ;

        // Signals that use error signal to find if there is one error on
        // each block, it is the or of previous signals
        logic [2:0] block_err_detected;
        logic [3:0] err_detected;
        logic [3:0] err_corrected;

        // variable for generate cycle
        generate
                case (AL_FT)
                        0 : begin
                                cv32e40p_aligner aligner_no_ft
                                (
                                        // Input ports of aligner_no_ft
                                        .clk                    (  clk                              ),
                                        .rst_n                  (  rst_n                            ),
                                        .fetch_valid_i          (  fetch_valid_i[0]                 ),
                                        .if_valid_i             (  if_valid_i[0]                    ),
                                        .fetch_rdata_i          (  fetch_rdata_i[0]                 ),
                                        .branch_addr_i          (  branch_addr_i[0]                 ),
                                        .branch_i               (  branch_i[0]                      ),
                                        .hwlp_addr_i            (  hwlp_addr_i[0]                   ),
                                        .hwlp_update_pc_i       (  hwlp_update_pc_i[0]              ),

                                        // Output ports of aligner_no_ft
                                        .aligner_ready_o        (  aligner_ready_o[0]               ),
                                        .instr_aligned_o        (  instr_aligned_o[0]               ),
                                        .instr_valid_o          (  instr_valid_o[0]                 ),
                                        .pc_o                   (  pc_o[0]                          )
                                );
                                // Since we don't use FT can't be detected an
                                // error
                                assign block_err_detected = {1'b0,1'b0,1'b0};
                        end
                        default : begin
                                // Input case 
                                case (AL_TIN) 
                                        0 : begin // Single input
                                                genvar i;
                                                for (i=0; i<3; i=i+1)  begin 
                                                        cv32e40p_aligner aligner_single_input
                                                        (
                                                                // Input ports of aligner_single_input
                                                                .clk                    (  clk                              ),
                                                                .rst_n                  (  rst_n                            ),
                                                                .fetch_valid_i          (  fetch_valid_i[0]                 ),
                                                                .if_valid_i             (  if_valid_i[0]                    ),
                                                                .fetch_rdata_i          (  fetch_rdata_i[0]                 ),
                                                                .branch_addr_i          (  branch_addr_i[0]                 ),
                                                                .branch_i               (  branch_i[0]                      ),
                                                                .hwlp_addr_i            (  hwlp_addr_i[0]                   ),
                                                                .hwlp_update_pc_i       (  hwlp_update_pc_i[0]              ),

                                                                // Output ports of aligner_single_input
                                                                .aligner_ready_o        (  aligner_ready_o_to_vote[i]       ),
                                                                .instr_aligned_o        (  instr_aligned_o_to_vote[i]       ),
                                                                .instr_valid_o          (  instr_valid_o_to_vote[i]         ),
                                                                .pc_o                   (  pc_o_to_vote[i]                  )
                                                        );
                                                end                                                
                                        end
                                        default : begin // Triplicated input
                                                genvar i;
                                                for (i=0; i<3; i=i+1)  begin 
                                                        cv32e40p_aligner aligner_tiple_input
                                                        (
                                                                // Input ports of aligner_tiple_input
                                                                .clk                    (  clk                              ),
                                                                .rst_n                  (  rst_n                            ),
                                                                .fetch_valid_i          (  fetch_valid_i[i]                 ),
                                                                .if_valid_i             (  if_valid_i[i]                    ),
                                                                .fetch_rdata_i          (  fetch_rdata_i[i]                 ),
                                                                .branch_addr_i          (  branch_addr_i[i]                 ),
                                                                .branch_i               (  branch_i[i]                      ),
                                                                .hwlp_addr_i            (  hwlp_addr_i[i]                   ),
                                                                .hwlp_update_pc_i       (  hwlp_update_pc_i[i]              ),

                                                                // Output ports of aligner_tiple_input
                                                                .aligner_ready_o        (  aligner_ready_o_to_vote[i]       ),
                                                                .instr_aligned_o        (  instr_aligned_o_to_vote[i]       ),
                                                                .instr_valid_o          (  instr_valid_o_to_vote[i]         ),
                                                                .pc_o                   (  pc_o_to_vote[i]                  )
                                                        );
                                                end        
                                        end
                                endcase        

                                 // Voter for TOVOTE signal, triple voter if
                                 // AL_TOUT[0] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(AL_TOUT[0])
                                 ) voter_aligner_ready_o_0
                                 (
                                          .to_vote_i( aligner_ready_o_to_vote ),
                                          .voted_o( aligner_ready_o),
                                          .block_err_o( aligner_ready_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[0]),
                                          .err_corrected_o(err_corrected[0])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // AL_TOUT[1] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(32),
                                          .TOUT(AL_TOUT[1])
                                 ) voter_instr_aligned_o_1
                                 (
                                          .to_vote_i( instr_aligned_o_to_vote ),
                                          .voted_o( instr_aligned_o),
                                          .block_err_o( instr_aligned_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[1]),
                                          .err_corrected_o(err_corrected[1])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // AL_TOUT[2] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(AL_TOUT[2])
                                 ) voter_instr_valid_o_2
                                 (
                                          .to_vote_i( instr_valid_o_to_vote ),
                                          .voted_o( instr_valid_o),
                                          .block_err_o( instr_valid_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[2]),
                                          .err_corrected_o(err_corrected[2])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // AL_TOUT[3] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(32),
                                          .TOUT(AL_TOUT[3])
                                 ) voter_pc_o_3
                                 (
                                          .to_vote_i( pc_o_to_vote ),
                                          .voted_o( pc_o),
                                          .block_err_o( pc_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[3]),
                                          .err_corrected_o(err_corrected[3])
                                 );
                                 
                                
                                assign err_detected_o =  err_detected[0]
                                                       | err_detected[1]
                                                       | err_detected[2]
                                                       | err_detected[3]; 
                                assign err_corrected_o =  err_corrected[0]
                                                        | err_corrected[1]
                                                        | err_corrected[2]
                                                        | err_corrected[3]; 
                                
                                assign block_err_detected[0] =  aligner_ready_o_block_err[0]
                                                              | instr_aligned_o_block_err[0]
                                                              | instr_valid_o_block_err[0]
                                                              | pc_o_block_err[0]; 
                                assign block_err_detected[1] =  aligner_ready_o_block_err[1]
                                                              | instr_aligned_o_block_err[1]
                                                              | instr_valid_o_block_err[1]
                                                              | pc_o_block_err[1]; 
                                assign block_err_detected[2] =  aligner_ready_o_block_err[2]
                                                              | instr_aligned_o_block_err[2]
                                                              | instr_valid_o_block_err[2]
                                                              | pc_o_block_err[2]; 
                                        
                                genvar m;
                                for (m=0;  m<3 ; m=m+1) begin 
                                        // This block is a counter that is incremented each
                                        // time there is an error and decremented when it
                                        // there is not. The value returned is is_broken_o
                                        // , if it is one the block is broken and should't be
                                        // used
                                        cv32e40p_breakage_monitor
                                        #(
                                                .DECREMENT(AL_DECREMENT),
                                                .INCREMENT(AL_INCREMENT),
                                                .BREAKING_THRESHOLD(AL_BREAKING_THRESHOLD),
                                                .COUNT_BIT(AL_COUNT_BIT),
                                                .INC_DEC_BIT(AL_INC_DEC_BIT)
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

