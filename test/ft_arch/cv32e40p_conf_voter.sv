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
//                                                                            //
//                                                                            //
// Design Name:    Compressed instruction decoder fault tolerant              //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Decodes RISC-V compressed instructions into their RV32     //
//                 equivalent. This module is fully combinatorial.            //
//                 Float extensions added                                     //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////

import cv32e40p_ft_pkg::*;


module cv32e40p_conf_voter
#(
 	parameter L1 = 32,
	parameter TOUT = 0 // triple out so triple voter
)
(
	input logic [2:0][L1-1:0] to_vote_i, // three input to vote
	input logic [2:0] broken_block_i, // this signal communicate if there is a broken block
	output logic [2:0][L1-1:0] voted_o, // voted output 
	output logic [2:0] block_err_o, // This signal said for each block if there is an error
	output logic err_detected_o, // Asserted if // Asserted if  
	output logic err_corrected_o // 
);

	logic [2:0][0:2] err;
	logic [2:0] err_detected;
	logic [2:0] err_corrected;
	
	generate
		case (TOUT)
			0: begin
				cv32e40p_3voter #(.L1(L1),.L2(1))  voter
				(
					.in_1_i( to_vote_i[0] ),
					.in_2_i( to_vote_i[1] ),
					.in_3_i( to_vote_i[2] ),
					.broken_block_i(broken_block_i),
					.voted_o( voted_o[0]),
					.err_detected_1_o(err[0][0]),
					.err_detected_2_o(err[0][1] ),
					.err_detected_3_o(err[0][2] ),
					.err_corrected_o(err_corrected_o),
					.err_detected_o(err_detected_o)
				);
				// Evaluate if there is an
				// error in the instr_o
				// signal in one of the three
				// block
				assign block_err_o = {    err[0][2],
							err[0][1],
							err[0][0]};
			end
			default: begin
				cv32e40p_3voter #(.L1(L1),.L2(1)) voter0
				(
					.in_1_i( to_vote_i[0] ),
					.in_2_i( to_vote_i[1] ),
					.in_3_i( to_vote_i[2] ),
					.broken_block_i(broken_block_i),
					.voted_o( voted_o[0]),
					.err_detected_1_o(err[0][0]),
					.err_detected_2_o(err[0][1] ),
					.err_detected_3_o(err[0][2] ),
					.err_corrected_o(err_corrected[0]),
					.err_detected_o(err_detected[0] )
				);

				cv32e40p_3voter #(.L1(L1),.L2(1)) voter1
				(
					.in_1_i( to_vote_i[0] ),
					.in_2_i( to_vote_i[1] ),
					.in_3_i( to_vote_i[2] ),
					.broken_block_i(broken_block_i),
					.voted_o( voted_o[1]),
					.err_detected_1_o(err[1][0]),
					.err_detected_2_o(err[1][1] ),
					.err_detected_3_o(err[1][2] ),
					.err_corrected_o(err_corrected[1]),
					.err_detected_o(err_detected[1])
				);
				cv32e40p_3voter #(.L1(L1),.L2(1)) voter2
				(
					.in_1_i( to_vote_i[0] ),
					.in_2_i( to_vote_i[1] ),
					.in_3_i( to_vote_i[2] ),
					.broken_block_i(broken_block_i),
					.voted_o( voted_o[2]),
					.err_detected_1_o(err[2][0]),
					.err_detected_2_o(err[2][1] ),
					.err_detected_3_o(err[2][2] ),
					.err_corrected_o(err_corrected[2]),
					.err_detected_o(err_detected[2])
				);
				assign block_err_o[0] =  (err[0][0] & err[1][0] & err[2][0])
                                                        | (err[0][0] & err[1][0])
                                                        | (err[1][0] & err[2][0]);
				assign block_err_o[1] =   (err[0][1] & err[1][1] & err[2][1])
                                                        | (err[0][1] & err[1][1])
                                                        | (err[1][1] & err[2][1]);
				assign block_err_o[2] =   (err[0][2] & err[1][2] & err[2][2])
                                                        | (err[0][2] & err[1][2])
                                                        | (err[1][2] & err[2][2]);
				assign err_detected_o =   (err_detected[0] & err_detected[1] & err_detected[2])
							| (err_detected[0] & err_detected[1])
							| (err_detected[1] & err_detected[2]);
				assign err_corrected_o =  (err_corrected[0] & err_corrected[1] & err_corrected[2])
							| (err_corrected[0] & err_corrected[1])
							| (err_corrected[1] & err_corrected[2]);
			end
		endcase
	endgenerate



endmodule
