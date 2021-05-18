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

import cv32e40p_pkg2::*;
import cv32e40p_pkg::*;

module cv32e40p_if_pipeline_ft
(

        // compressed decoder input output
        input logic [2:0]          [31:0]   instr_decompressed,
        input logic [2:0]                   instr_compressed_int,
        input logic [2:0]          [31:0]   pc_if_o,
        input logic [2:0]                   fetch_failed,
        input logic [2:0]                   id_ready_i,
        input logic [2:0]                   halt_if_i,
        input logic [2:0]                   instr_valid,
        input logic [2:0]                   clear_instr_valid_i,
        input logic [2:0]                   illegal_c_insn,
        input logic [2:0]                   fetch_valid,
        output logic [2:0]                   instr_valid_id_o,
        output logic [2:0]          [31:0]   instr_rdata_id_o,
        output logic [2:0]                   is_fetch_failed_o,
        output logic [2:0]          [31:0]   pc_id_o,
        output logic [2:0]                   is_compressed_id_o,
        output logic [2:0]                   illegal_c_insn_id_o,
        output logic [2:0]                   if_valid,

        input logic clk,
        input logic rst_n,                

        // fault tolerant state
        input logic [2:0] set_broken_i,
        output logic [2:0] is_broken_o,
        output logic err_detected_o,
        output logic err_corrected_o
);
        // Signals out to each compressed decoder block to be voted
        logic [2:0]                   instr_valid_id_o_to_vote ;
        logic [2:0]          [31:0]   instr_rdata_id_o_to_vote ;
        logic [2:0]                   is_fetch_failed_o_to_vote ;
        logic [2:0]          [31:0]   pc_id_o_to_vote ;
        logic [2:0]                   is_compressed_id_o_to_vote ;
        logic [2:0]                   illegal_c_insn_id_o_to_vote ;
        logic [2:0]                   if_valid_to_vote ;

        // Error signals
        logic [2:0] instr_valid_id_o_block_err ;
        logic [2:0] instr_rdata_id_o_block_err ;
        logic [2:0] is_fetch_failed_o_block_err ;
        logic [2:0] pc_id_o_block_err ;
        logic [2:0] is_compressed_id_o_block_err ;
        logic [2:0] illegal_c_insn_id_o_block_err ;
        logic [2:0] if_valid_block_err ;

        // Signals that use error signal to find if there is one error on
        // each block, it is the or of previous signals
        logic [2:0] block_err_detected;
        logic [6:0] err_detected;
        logic [6:0] err_corrected;

        // variable for generate cycle
        generate
                case (IFPI_FT)
                        0 : begin
                                cv32e40p_if_pipeline if_pipeline_no_ft
                                (
                                        // Input ports of if_pipeline_no_ft
                                        .rst_n                  (  rst_n                            ),
                                        .instr_decompressed     (  instr_decompressed[0]            ),
                                        .instr_compressed_int   (  instr_compressed_int[0]          ),
                                        .pc_if_o                (  pc_if_o[0]                       ),
                                        .fetch_failed           (  fetch_failed[0]                  ),
                                        .id_ready_i             (  id_ready_i[0]                    ),
                                        .halt_if_i              (  halt_if_i[0]                     ),
                                        .instr_valid            (  instr_valid[0]                   ),
                                        .clear_instr_valid_i    (  clear_instr_valid_i[0]           ),
                                        .illegal_c_insn         (  illegal_c_insn[0]                ),
                                        .fetch_valid            (  fetch_valid[0]                   ),
                                        .clk                    (  clk                              ),

                                        // Output ports of if_pipeline_no_ft
                                        .instr_valid_id_o       (  instr_valid_id_o[0]              ),
                                        .instr_rdata_id_o       (  instr_rdata_id_o[0]              ),
                                        .is_fetch_failed_o      (  is_fetch_failed_o[0]             ),
                                        .pc_id_o                (  pc_id_o[0]                       ),
                                        .is_compressed_id_o     (  is_compressed_id_o[0]            ),
                                        .illegal_c_insn_id_o    (  illegal_c_insn_id_o[0]           ),
                                        .if_valid               (  if_valid[0]                      )
                                );
                                // Since we don't use FT can't be detected an
                                // error
                                assign block_err_detected = {1'b0,1'b0,1'b0};
                        end
                        default : begin
                                // Input case 
                                case (IFPI_TIN) 
                                        0 : begin // Single input
                                                genvar i;
                                                for (i=0; i<3; i=i+1)  begin 
                                                        cv32e40p_if_pipeline if_pipeline_single_input
                                                        (
                                                                // Input ports of if_pipeline_single_input
                                                                .rst_n                  (  rst_n                            ),
                                                                .instr_decompressed     (  instr_decompressed[0]            ),
                                                                .instr_compressed_int   (  instr_compressed_int[0]          ),
                                                                .pc_if_o                (  pc_if_o[0]                       ),
                                                                .fetch_failed           (  fetch_failed[0]                  ),
                                                                .id_ready_i             (  id_ready_i[0]                    ),
                                                                .halt_if_i              (  halt_if_i[0]                     ),
                                                                .instr_valid            (  instr_valid[0]                   ),
                                                                .clear_instr_valid_i    (  clear_instr_valid_i[0]           ),
                                                                .illegal_c_insn         (  illegal_c_insn[0]                ),
                                                                .fetch_valid            (  fetch_valid[0]                   ),
                                                                .clk                    (  clk                              ),

                                                                // Output ports of if_pipeline_single_input
                                                                .instr_valid_id_o       (  instr_valid_id_o_to_vote[i]      ),
                                                                .instr_rdata_id_o       (  instr_rdata_id_o_to_vote[i]      ),
                                                                .is_fetch_failed_o      (  is_fetch_failed_o_to_vote[i]     ),
                                                                .pc_id_o                (  pc_id_o_to_vote[i]               ),
                                                                .is_compressed_id_o     (  is_compressed_id_o_to_vote[i]    ),
                                                                .illegal_c_insn_id_o    (  illegal_c_insn_id_o_to_vote[i]   ),
                                                                .if_valid               (  if_valid_to_vote[i]              )
                                                        );
                                                end                                                
                                        end
                                        default : begin // Triplicated input
                                                genvar i;
                                                for (i=0; i<3; i=i+1)  begin 
                                                        cv32e40p_if_pipeline if_pipeline_tiple_input
                                                        (
                                                                // Input ports of if_pipeline_tiple_input
                                                                .rst_n                  (  rst_n                            ),
                                                                .instr_decompressed     (  instr_decompressed[i]            ),
                                                                .instr_compressed_int   (  instr_compressed_int[i]          ),
                                                                .pc_if_o                (  pc_if_o[i]                       ),
                                                                .fetch_failed           (  fetch_failed[i]                  ),
                                                                .id_ready_i             (  id_ready_i[i]                    ),
                                                                .halt_if_i              (  halt_if_i[i]                     ),
                                                                .instr_valid            (  instr_valid[i]                   ),
                                                                .clear_instr_valid_i    (  clear_instr_valid_i[i]           ),
                                                                .illegal_c_insn         (  illegal_c_insn[i]                ),
                                                                .fetch_valid            (  fetch_valid[i]                   ),
                                                                .clk                    (  clk                              ),

                                                                // Output ports of if_pipeline_tiple_input
                                                                .instr_valid_id_o       (  instr_valid_id_o_to_vote[i]      ),
                                                                .instr_rdata_id_o       (  instr_rdata_id_o_to_vote[i]      ),
                                                                .is_fetch_failed_o      (  is_fetch_failed_o_to_vote[i]     ),
                                                                .pc_id_o                (  pc_id_o_to_vote[i]               ),
                                                                .is_compressed_id_o     (  is_compressed_id_o_to_vote[i]    ),
                                                                .illegal_c_insn_id_o    (  illegal_c_insn_id_o_to_vote[i]   ),
                                                                .if_valid               (  if_valid_to_vote[i]              )
                                                        );
                                                end        
                                        end
                                endcase        

                                 // Voter for TOVOTE signal, triple voter if
                                 // IFPI_TOUT[0] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(IFPI_TOUT[0])
                                 ) voter_instr_valid_id_o_0
                                 (
                                          .to_vote_i( instr_valid_id_o_to_vote ),
                                          .voted_o( instr_valid_id_o),
                                          .block_err_o( instr_valid_id_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[0]),
                                          .err_corrected_o(err_corrected[0])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // IFPI_TOUT[1] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(32),
                                          .TOUT(IFPI_TOUT[1])
                                 ) voter_instr_rdata_id_o_1
                                 (
                                          .to_vote_i( instr_rdata_id_o_to_vote ),
                                          .voted_o( instr_rdata_id_o),
                                          .block_err_o( instr_rdata_id_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[1]),
                                          .err_corrected_o(err_corrected[1])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // IFPI_TOUT[2] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(IFPI_TOUT[2])
                                 ) voter_is_fetch_failed_o_2
                                 (
                                          .to_vote_i( is_fetch_failed_o_to_vote ),
                                          .voted_o( is_fetch_failed_o),
                                          .block_err_o( is_fetch_failed_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[2]),
                                          .err_corrected_o(err_corrected[2])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // IFPI_TOUT[3] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(32),
                                          .TOUT(IFPI_TOUT[3])
                                 ) voter_pc_id_o_3
                                 (
                                          .to_vote_i( pc_id_o_to_vote ),
                                          .voted_o( pc_id_o),
                                          .block_err_o( pc_id_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[3]),
                                          .err_corrected_o(err_corrected[3])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // IFPI_TOUT[4] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(IFPI_TOUT[4])
                                 ) voter_is_compressed_id_o_4
                                 (
                                          .to_vote_i( is_compressed_id_o_to_vote ),
                                          .voted_o( is_compressed_id_o),
                                          .block_err_o( is_compressed_id_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[4]),
                                          .err_corrected_o(err_corrected[4])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // IFPI_TOUT[5] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(IFPI_TOUT[5])
                                 ) voter_illegal_c_insn_id_o_5
                                 (
                                          .to_vote_i( illegal_c_insn_id_o_to_vote ),
                                          .voted_o( illegal_c_insn_id_o),
                                          .block_err_o( illegal_c_insn_id_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[5]),
                                          .err_corrected_o(err_corrected[5])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // IFPI_TOUT[6] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(IFPI_TOUT[6])
                                 ) voter_if_valid_6
                                 (
                                          .to_vote_i( if_valid_to_vote ),
                                          .voted_o( if_valid),
                                          .block_err_o( if_valid_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[6]),
                                          .err_corrected_o(err_corrected[6])
                                 );
                                 
                                
                                assign err_detected_o =  err_detected[0]
                                                       | err_detected[1]
                                                       | err_detected[2]
                                                       | err_detected[3]
                                                       | err_detected[4]
                                                       | err_detected[5]
                                                       | err_detected[6]; 
                                assign err_corrected_o =  err_corrected[0]
                                                        | err_corrected[1]
                                                        | err_corrected[2]
                                                        | err_corrected[3]
                                                        | err_corrected[4]
                                                        | err_corrected[5]
                                                        | err_corrected[6]; 
                                
                                assign block_err_detected[0] =  instr_valid_id_o_block_err[0]
                                                              | instr_rdata_id_o_block_err[0]
                                                              | is_fetch_failed_o_block_err[0]
                                                              | pc_id_o_block_err[0]
                                                              | is_compressed_id_o_block_err[0]
                                                              | illegal_c_insn_id_o_block_err[0]
                                                              | if_valid_block_err[0]; 
                                assign block_err_detected[1] =  instr_valid_id_o_block_err[1]
                                                              | instr_rdata_id_o_block_err[1]
                                                              | is_fetch_failed_o_block_err[1]
                                                              | pc_id_o_block_err[1]
                                                              | is_compressed_id_o_block_err[1]
                                                              | illegal_c_insn_id_o_block_err[1]
                                                              | if_valid_block_err[1]; 
                                assign block_err_detected[2] =  instr_valid_id_o_block_err[2]
                                                              | instr_rdata_id_o_block_err[2]
                                                              | is_fetch_failed_o_block_err[2]
                                                              | pc_id_o_block_err[2]
                                                              | is_compressed_id_o_block_err[2]
                                                              | illegal_c_insn_id_o_block_err[2]
                                                              | if_valid_block_err[2]; 
                                        
                                genvar m;
                                for (m=0;  m<3 ; m=m+1) begin 
                                        // This block is a counter that is incremented each
                                        // time there is an error and decremented when it
                                        // there is not. The value returned is is_broken_o
                                        // , if it is one the block is broken and should't be
                                        // used
                                        cv32e40p_breakage_monitor
                                        #(
                                                .DECREMENT(IFPI_DECREMENT),
                                                .INCREMENT(IFPI_INCREMENT),
                                                .BREAKING_THRESHOLD(IFPI_BREAKING_THRESHOLD),
                                                .COUNT_BIT(IFPI_COUNT_BIT),
                                                .INC_DEC_BIT(IFPI_INC_DEC_BIT)
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

