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

module cv32e40p_compressed_decoder_ft
#(
        parameter FPU                 = 0
)
(

        // compressed decoder input output
        input logic [2:0]          [31:0]   instr_i,
        output logic [2:0]          [31:0]   instr_o,
        output logic [2:0]                   is_compressed_o,
        output logic [2:0]                   illegal_instr_o,

        input logic clk,
        input logic rst_n,                

        // fault tolerant state
        input logic [2:0] set_broken_i,
        output logic [2:0] is_broken_o,
        output logic err_detected_o,
        output logic err_corrected_o
);
        // Signals out to each compressed decoder block to be voted
        logic [2:0]          [31:0]   instr_o_to_vote ;
        logic [2:0]                   is_compressed_o_to_vote ;
        logic [2:0]                   illegal_instr_o_to_vote ;

        // Error signals
        logic [2:0] instr_o_block_err ;
        logic [2:0] is_compressed_o_block_err ;
        logic [2:0] illegal_instr_o_block_err ;

        // Signals that use error signal to find if there is one error on
        // each block, it is the or of previous signals
        logic [2:0] block_err_detected;
        logic [2:0] err_detected;
        logic [2:0] err_corrected;

        // variable for generate cycle
        generate
                case (CODE_FT)
                        0 : begin
                                cv32e40p_compressed_decoder
                                #( 
                                         .FPU                 (  FPU                 ) 
                                )
                                 compressed_decoder_no_ft
                                (
                                        // Input ports of compressed_decoder_no_ft
                                        .instr_i                (  instr_i[0]                       ),

                                        // Output ports of compressed_decoder_no_ft
                                        .instr_o                (  instr_o[0]                       ),
                                        .is_compressed_o        (  is_compressed_o[0]               ),
                                        .illegal_instr_o        (  illegal_instr_o[0]               )
                                );
                                // Since we don't use FT can't be detected an
                                // error
                                assign block_err_detected = {1'b0,1'b0,1'b0};
                        end
                        default : begin
                                // Input case 
                                case (CODE_TIN) 
                                        0 : begin // Single input
                                                genvar i;
                                                for (i=0; i<3; i=i+1)  begin 
                                                        cv32e40p_compressed_decoder
                                                        #( 
                                                                 .FPU                 (  FPU                 ) 
                                                        )
                                                         compressed_decoder_single_input
                                                        (
                                                                // Input ports of compressed_decoder_single_input
                                                                .instr_i                (  instr_i[0]                       ),

                                                                // Output ports of compressed_decoder_single_input
                                                                .instr_o                (  instr_o_to_vote[i]               ),
                                                                .is_compressed_o        (  is_compressed_o_to_vote[i]       ),
                                                                .illegal_instr_o        (  illegal_instr_o_to_vote[i]       )
                                                        );
                                                end                                                
                                        end
                                        default : begin // Triplicated input
                                                genvar i;
                                                for (i=0; i<3; i=i+1)  begin 
                                                        cv32e40p_compressed_decoder
                                                        #( 
                                                                 .FPU                 (  FPU                 ) 
                                                        )
                                                         compressed_decoder_tiple_input
                                                        (
                                                                // Input ports of compressed_decoder_tiple_input
                                                                .instr_i                (  instr_i[i]                       ),

                                                                // Output ports of compressed_decoder_tiple_input
                                                                .instr_o                (  instr_o_to_vote[i]               ),
                                                                .is_compressed_o        (  is_compressed_o_to_vote[i]       ),
                                                                .illegal_instr_o        (  illegal_instr_o_to_vote[i]       )
                                                        );
                                                end        
                                        end
                                endcase        

                                 // Voter for TOVOTE signal, triple voter if
                                 // CODE_TOUT[0] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(32),
                                          .TOUT(CODE_TOUT[0])
                                 ) voter_instr_o_0
                                 (
                                          .to_vote_i( instr_o_to_vote ),
                                          .voted_o( instr_o),
                                          .block_err_o( instr_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[0]),
                                          .err_corrected_o(err_corrected[0])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // CODE_TOUT[1] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(CODE_TOUT[1])
                                 ) voter_is_compressed_o_1
                                 (
                                          .to_vote_i( is_compressed_o_to_vote ),
                                          .voted_o( is_compressed_o),
                                          .block_err_o( is_compressed_o_block_err),
                                          .broken_block_i(is_broken_o),
                                          .err_detected_o(err_detected[1]),
                                          .err_corrected_o(err_corrected[1])
                                 );
                                 
                                 // Voter for TOVOTE signal, triple voter if
                                 // CODE_TOUT[2] == 1
                                 cv32e40p_conf_voter
                                 #(
                                          .L1(1),
                                          .TOUT(CODE_TOUT[2])
                                 ) voter_illegal_instr_o_2
                                 (
                                          .to_vote_i( illegal_instr_o_to_vote ),
                                          .voted_o( illegal_instr_o),
                                          .block_err_o( illegal_instr_o_block_err),
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
                                
                                assign block_err_detected[0] =  instr_o_block_err[0]
                                                              | is_compressed_o_block_err[0]
                                                              | illegal_instr_o_block_err[0]; 
                                assign block_err_detected[1] =  instr_o_block_err[1]
                                                              | is_compressed_o_block_err[1]
                                                              | illegal_instr_o_block_err[1]; 
                                assign block_err_detected[2] =  instr_o_block_err[2]
                                                              | is_compressed_o_block_err[2]
                                                              | illegal_instr_o_block_err[2]; 
                                        
                                genvar m;
                                for (m=0;  m<3 ; m=m+1) begin 
                                        // This block is a counter that is incremented each
                                        // time there is an error and decremented when it
                                        // there is not. The value returned is is_broken_o
                                        // , if it is one the block is broken and should't be
                                        // used
                                        cv32e40p_breakage_monitor
                                        #(
                                                .DECREMENT(CODE_DECREMENT),
                                                .INCREMENT(CODE_INCREMENT),
                                                .BREAKING_THRESHOLD(CODE_BREAKING_THRESHOLD),
                                                .COUNT_BIT(CODE_COUNT_BIT),
                                                .INC_DEC_BIT(CODE_INC_DEC_BIT)
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

