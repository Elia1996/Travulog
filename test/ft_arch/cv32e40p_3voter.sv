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

module cv32e40p_3voter
#(
  parameter L1 = 32,
  parameter L2 = 1
)
(
  input  logic [L1-1:0][L2-1:0]   	in_1_i,
  input  logic [L1-1:0][L2-1:0]   	in_2_i,
  input  logic [L1-1:0][L2-1:0]   	in_3_i,
  input  logic [2:0]		      	broken_block_i,

  output logic [L1-1:0][L2-1:0]		voted_o,
  output logic				err_detected_1_o,
  output logic 				err_detected_2_o,
  output logic				err_detected_3_o,
  output logic                  	err_corrected_o,
  output logic				err_detected_o
);

	//structural description of majority voter of 3

	always_comb
	begin
		case (broken_block_i) 
			3'b001: begin  // the first input is broken
				voted_o=in_2_i;
				if (in_2_i!=in_3_i) begin
					err_detected_2_o = 1'b1;
					err_detected_3_o = 1'b1;
					err_corrected_o  = 1'b0;
				end else begin
					err_detected_2_o = 1'b0;
					err_detected_3_o = 1'b0;
					err_corrected_o  = 1'b0;
				end
			end
			3'b010: begin  // the second input is broken
				voted_o=in_3_i;
				if (in_1_i!=in_3_i) begin
					err_detected_1_o = 1'b1;
					err_detected_3_o = 1'b1;
					err_corrected_o  = 1'b0;
				end else begin
					err_detected_1_o = 1'b0;
					err_detected_3_o = 1'b0;
					err_corrected_o  = 1'b0;
				end
			end

			3'b100: begin  // the third input is broken
				voted_o=in_1_i;
				if (in_1_i!=in_2_i) begin
					err_detected_1_o = 1'b1;
					err_detected_2_o = 1'b1;
					err_corrected_o  = 1'b0;
				end else begin
					err_detected_1_o = 1'b0;
					err_detected_2_o = 1'b0;
					err_corrected_o  = 1'b0;
				end
			end

			default: begin // if is not true that only two inputs can be correct	
				if (in_1_i!=in_2_i && in_1_i!=in_3_i && in_2_i!=in_3_i) begin // the 3 outputs are all different
					err_detected_1_o = 1'b1;
					err_detected_2_o = 1'b1;
					err_detected_3_o = 1'b1;
					err_corrected_o = 1'b0;
					voted_o = in_1_i; //default output if the outputs are all different
				end
				else begin
					if (in_2_i!=in_3_i) begin
						err_corrected_o = 1'b1;
						voted_o = in_1_i;
						if (in_2_i==in_1_i) begin
							err_detected_1_o = 1'b0;
							err_detected_2_o = 1'b0;
							err_detected_3_o = 1'b1;			
						end
						else begin
							err_detected_1_o = 1'b0;
							err_detected_2_o = 1'b1;
							err_detected_3_o = 1'b0;
						end
					end 
					else begin
						voted_o=in_2_i;
						if (in_2_i!=in_1_i) begin
							err_detected_1_o = 1'b1;
							err_detected_2_o = 1'b0;
							err_detected_3_o = 1'b0;
							err_corrected_o = 1'b1;
						end
						else begin// the 3 outputs are all equal
							err_detected_1_o = 1'b0;
							err_detected_2_o = 1'b0;
							err_detected_3_o = 1'b0;
							err_corrected_o = 1'b0;
						end
					end
				end
			end
				
		endcase
	end

	assign err_detected_o = err_detected_1_o || err_detected_2_o || err_detected_3_o;

endmodule
