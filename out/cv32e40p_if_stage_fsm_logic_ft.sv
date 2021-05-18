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

module cv32e40p_if_stage_fsm_logic_ft
(

        // compressed decoder input output
        input logic [2:0]                   pc_set_i,
        input logic [2:0]                   fetch_valid,
        input logic [2:0]                   req_i,
        input logic [2:0]                   if_valid,
        input logic [2:0]                   aligner_ready,
        output logic [2:0]                   branch_req,
        output logic [2:0]                   fetch_ready,
        output logic [2:0]                   perf_imiss_o,

        input logic clk,
        input logic rst_n,                

        // fault tolerant state
        input logic [2:0] set_broken_i,
        output logic [2:0] is_broken_o,
        output logic err_detected_o,
        output logic err_corrected_o
);
        // Signals out to each compressed decoder block to be voted
        logic [2:0]                   branch_req_to_vote ;
        logic [2:0]                   fetch_ready_to_vote ;
        logic [2:0]                   perf_imiss_o_to_vote ;

        // Error signals
        logic [2:0] branch_req_block_err ;
        logic [2:0] fetch_ready_block_err ;
        logic [2:0] perf_imiss_o_block_err ;

        // Signals that use error signal to find if there is one error on
        // each block, it is the or of previous signals
        logic [2:0] block_err_detected;
        logic [2:0] err_detected;
        logic [2:0] err_corrected;

        // variable for generate cycle
        generate
                case (IFSTFSLO_FT)
                        0 : begin
                                cv32e40p_if_stage_fsm_logic if_stage_fsm_logic_no_ft
                                (
                                        // Input ports of if_stage_fsm_logic_no_ft
                                        .pc_set_i               (  pc_set_i[0]                      ),
                                        .fetch_valid            (  fetch_valid[0]                   ),
                                        .req_i                  (  req_i[0]                         ),
                                        .if_valid               (  if_valid[0]                      ),
                                        .aligner_ready          (  aligner_ready[0]                 ),

                                        // Output ports of if_stage_fsm_logic_no_ft
                                        .branch_req             (  branch_req[0]                    ),
                                        .fetch_ready            (  fetch_ready[0]                   ),
                                        .perf_imiss_o           (  perf_imiss_o[0]                  )
                                );
                                // Since we don't use FT can't be detected an
                                // error
                                assign block_err_detected = {1'b0,1'b0,1'b0};
                        end
                        default : begin
                                // Input case 
                                case (IFSTFSLO_TIN) 
                                        0 : begin // Single input
                                                genvar i;
                                                for (i=0; i<3; i=i+1)  begin 
                                                        cv32e40p_if_stage_fsm_logic if_stage_fsm_logic_single_input
                                                        (
                                                                // Input ports of if_stage_fsm_logic_single_input
                                                                .pc_set_i               (  pc_set_i[0]                      ),
                                                                .fetch_valid            (  fetch_valid[0]                   ),
                                                                .req_i                  (  req_i[0]                         ),
                                                                .if_valid               (  if_valid[0]                      ),
                                                                .aligner_ready          (  aligner_ready[0]                 ),

                                                                // Output ports of if_stage_fsm_logic_single_input
                                                                .branch_req             (  branch_req_to_vote[i]            ),
                                                                .fetch_ready            (  fetch_ready_to_vote[i]           ),
                                                                .perf_imiss_o           (  perf_imiss_o_to_vote[i]          )
                                                        );
                                                end                                                
                                        end
                                        default : begin // Triplicated input
                                                genvar i;
                                                for (i=0; i<3; i=i+1)  begin 
                                                        cv32e40p_if_stage_fsm_logic if_stage_fsm_logic_tiple_input
                                                        (
                                                                // Input ports of if_stage_fsm_logic_tiple_input
                                                                .pc_set_i               (  pc_set_i[i]                      ),
                                                                .fetch_valid            (  fetch_valid[i]                   ),
                                                                .req_i                  (  req_i[i]                         ),
                                                                .if_valid               (  if_valid[i]                      ),
                                                                .aligner_ready          (  aligner_ready[i]                 ),

                                                                // Output ports of if_stage_fsm_logic_tiple_input
                                                                .branch_req             (  branch_req_to_vote[i]            ),
                                                                .fetch_ready            (  fetch_ready_to_vote[i]           ),
                                                                .perf_imiss_o           (  perf_imiss_o_to_vote[i]          )
                                                        );
                                                end        
                                        end
                                endcase        

                                 // Voter for TOVOTE signal, triple voter if
                                 // IFSTFSLO_TOUT[0] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(IFSTFSLO_TOUT[0])
                                 ) voter_branch_req_0
                                 (
                                          .to_vote_i( branch_req_to_vote ),
                                          .voted_o( branch_req),
                                          .block_err_o( branch_req_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[0]),
                                          .err_corrected_o(err_corrected[0])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // IFSTFSLO_TOUT[1] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(IFSTFSLO_TOUT[1])
                                 ) voter_fetch_ready_1
                                 (
                                          .to_vote_i( fetch_ready_to_vote ),
                                          .voted_o( fetch_ready),
                                          .block_err_o( fetch_ready_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[1]),
                                          .err_corrected_o(err_corrected[1])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // IFSTFSLO_TOUT[2] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(IFSTFSLO_TOUT[2])
                                 ) voter_perf_imiss_o_2
                                 (
                                          .to_vote_i( perf_imiss_o_to_vote ),
                                          .voted_o( perf_imiss_o),
                                          .block_err_o( perf_imiss_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[2]),
                                          .err_corrected_o(err_corrected[2])
                                 );
                                 
                                
                                assign err_detected_o =  err_detected[0]
                                                       | err_detected[1]
                                                       | err_detected[2]; 
                                assign err_corrected_o =  err_corrected[0]
                                                        | err_corrected[1]
                                                        | err_corrected[2]; 
                                
                                assign block_err_detected[0] =  branch_req_block_err[0]
                                                              | fetch_ready_block_err[0]
                                                              | perf_imiss_o_block_err[0]; 
                                assign block_err_detected[1] =  branch_req_block_err[1]
                                                              | fetch_ready_block_err[1]
                                                              | perf_imiss_o_block_err[1]; 
                                assign block_err_detected[2] =  branch_req_block_err[2]
                                                              | fetch_ready_block_err[2]
                                                              | perf_imiss_o_block_err[2]; 
                                        
                                genvar m;
                                for (m=0;  m<3 ; m=m+1) begin 
                                        // This block is a counter that is incremented each
                                        // time there is an error and decremented when it
                                        // there is not. The value returned is is_broken_o
                                        // , if it is one the block is broken and should't be
                                        // used
                                        cv32e40p_breakage_monitor
                                        #(
                                                .DECREMENT(IFSTFSLO_DECREMENT),
                                                .INCREMENT(IFSTFSLO_INCREMENT),
                                                .BREAKING_THRESHOLD(IFSTFSLO_BREAKING_THRESHOLD),
                                                .COUNT_BIT(IFSTFSLO_COUNT_BIT),
                                                .INC_DEC_BIT(IFSTFSLO_INC_DEC_BIT)
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

