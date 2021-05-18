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

module MODULE_NAME
	PARAMETER_DECLARATION BLOCK
(

	// compressed decoder input output
	DECLARATION_FOREACH BLOCK IN_OUT NOT clk rst_n
		INOUT logic [2:0]BITINIT SIGNAME,
	END_DECLARATION_FOREACH
	
	input logic clk,
	input logic rst_n,		

	// fault tolerant state
        input logic [2:0] set_broken_i,
        output logic [2:0] is_broken_o,
        output logic err_detected_o,
        output logic err_corrected_o
);
	// Signals out to each compressed decoder block to be voted
	DECLARATION_FOREACH BLOCK OUT
		logic [2:0]BITINIT SIGNAME_to_vote ;
	END_DECLARATION_FOREACH
		
	// Error signals
	DECLARATION_FOREACH BLOCK OUT
		logic [2:0] SIGNAME_block_err ;	
	END_DECLARATION_FOREACH

        // Signals that use error signal to find if there is one error on
        // each block, it is the or of previous signals
        logic [2:0] block_err_detected;
        logic [SIG_NUM-BLOCK-OUT:0] err_detected;
        logic [SIG_NUM-BLOCK-OUT:0] err_corrected;

	// variable for generate cycle
	generate
		case (PARAM_NAME_FT)
			0 : begin
				INSTANCE BLOCK BLOCK_MODNAME_no_ft
					PARAM=PARAM
					IF clk rst_n IN=IN
					IN= IN[0]
					OUT = OUT[0]
				END_INSTANCE
				// Since we don't use FT can't be detected an
				// error
				assign block_err_detected = {1'b0,1'b0,1'b0};
			end
			default : begin
				// Input case 
				case (PARAM_NAME_TIN) 
					0 : begin // Single input
						genvar i;
						for (i=0; i<3; i=i+1)  begin 
							INSTANCE BLOCK BLOCK_MODNAME_single_input 
								PARAM=PARAM
								IF clk rst_n IN=IN
								IN=IN[0] 
								OUT = OUT_to_vote[i]
							END_INSTANCE
						end						
					end
					default : begin // Triplicated input
						genvar i;
						for (i=0; i<3; i=i+1)  begin 
							INSTANCE BLOCK BLOCK_MODNAME_tiple_input
								PARAM=PARAM
								IF clk rst_n IN=IN
								IN = IN[i]
								OUT = OUT_to_vote[i]
							END_INSTANCE
						end	
					end
				endcase	

			 	INSTANCE_FOREACH BLOCK OUT	
					// Voter for TOVOTE signal, triple voter if
					// PARAM_NAME_TOUT[INDEX] == 1
					cv32e40p_conf_voter
					#(
						.L1(BITNUMBER),
						.TOUT(PARAM_NAME_TOUT[INDEX])
					) voter_SIGNAME_INDEX
					(
						.to_vote_i( SIGNAME_to_vote ),
						.voted_o( SIGNAME),
						.block_err_o( SIGNAME_block_err),
						.broken_block_i(is_broken_o),
						.err_detected_o(err_detected[INDEX]),
						.err_corrected_o(err_corrected[INDEX])
					);
				END_INSTANCE_FOREACH
				
				assign err_detected_o = OP_FOREACH BLOCK OUT | err_detected[INDEX] ;
				assign err_corrected_o = OP_FOREACH BLOCK OUT | err_corrected[INDEX] ;
				
				assign block_err_detected[0] = OP_FOREACH BLOCK OUT | SIGNAME_block_err[0] ; 
				assign block_err_detected[1] = OP_FOREACH BLOCK OUT | SIGNAME_block_err[1] ; 
				assign block_err_detected[2] = OP_FOREACH BLOCK OUT | SIGNAME_block_err[2] ; 
					
				genvar m;
				for (m=0;  m<3 ; m=m+1) begin 
					// This block is a counter that is incremented each
					// time there is an error and decremented when it
					// there is not. The value returned is is_broken_o
					// , if it is one the block is broken and should't be
					// used
					cv32e40p_breakage_monitor
					#(
						.DECREMENT(PARAM_NAME_DECREMENT),
						.INCREMENT(PARAM_NAME_INCREMENT),
						.BREAKING_THRESHOLD(PARAM_NAME_BREAKING_THRESHOLD),
						.COUNT_BIT(PARAM_NAME_COUNT_BIT),
						.INC_DEC_BIT(PARAM_NAME_INC_DEC_BIT)
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
