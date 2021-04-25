// Copyright 2020 Politecnico di Torino.


////////////////////////////////////////////////////////////////////////////////
//                                                                            //
// Engineer:       Elia Ribaldone - s265613@studenti.polito.it                //
//                                                                            //
// Additional contributions by:                                               //
//                                                                            //
// 		   Luca Fiore - luca.fiore@studenti.polito.it                 //
//                 Marcello Neri - s257090@studenti.polito.it                 //
//                                                                            //
//                                                                            //
// Design Name:    cv32e40p_voter                                             //
// Project Name:   cv32e40p Fault tolernat                                    //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    count error detected and decide if the                     //
//                 component is broken.                                       //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////


module cv32e40p_breakage_monitor
#(
	parameter int DECREMENT = 1,
	parameter int INCREMENT = 1,
	parameter int BREAKING_THRESHOLD = 100,
	parameter int COUNT_BIT = 8,
	parameter int INC_DEC_BIT = 2
)
(
	input logic rst_n,
	input logic clk,
	input logic err_detected_i,
	input logic set_broken_i,
	output logic is_broken_o
);

	// Register variables
	logic [COUNT_BIT-1:0] reg_count_n;
	logic [COUNT_BIT-1:0] reg_count_q;
	logic reg_is_broken_n;
	logic reg_is_broken_q;
	logic [INC_DEC_BIT-1:0] reg_increment_n;
	logic [INC_DEC_BIT-1:0] reg_decrement_n;
	logic [COUNT_BIT-1:0] reg_threshold_n;

	// increment/decrement selection variable
	logic [INC_DEC_BIT-1:0] real_dec;
	logic [INC_DEC_BIT-1:0] real_inc;
	logic count_all_ones;
	logic count_all_zeros;
	logic err_detected;
	logic is_broken;

	// Clock gated
	logic clk_gated ;

	// reg_count -> counter register to count errors, if there are error
	// 		it is incremented of INCREMENT otherwise it is
	// 		 decremented of DECREMENT
	// reg_is_broken -> this register is set to one when the block is 
	// 		broken, when this happen the breakage_monitor is
	// 		halted, clock is gated and is_broken_o remain to
	// 		1 indefinetly
	always_ff @ (posedge clk_gated or negedge rst_n) begin
		if (!rst_n) begin
			reg_count_n <= {COUNT_BIT{1'b0}};
			reg_is_broken_n <= 1'b0;

			// init to 0 the register to store parameter
			reg_increment_n <= {INC_DEC_BIT{1'b0}};
			reg_decrement_n <= {INC_DEC_BIT{1'b0}};
			reg_threshold_n <= {COUNT_BIT{1'b0}};
		end else begin
			reg_count_n <= reg_count_q;
			reg_is_broken_n <= reg_is_broken_q;

			// register to store parameter
			reg_increment_n <= INCREMENT;
			reg_decrement_n <= DECREMENT;
			reg_threshold_n <= BREAKING_THRESHOLD;
		end
	end
	
	
	always_comb begin
		// increment/decrement selection
		count_all_ones = &reg_count_n; // and on count register output
		count_all_zeros =  &(~reg_count_n); // nand on count register output

		// If the component is broken, err detected is halted to avoid
		// unnecessary switch
		if (reg_is_broken_n == 1'b1)
			err_detected = 1'b0;
		else 
			err_detected = err_detected_i;

		// Select value to add or decrement to reg_count_n
		if (err_detected) begin // If there is an error we increment the register
			// we don't increment if reg_count is full
			if (count_all_ones == 1'b1) 
				real_inc = {INC_DEC_BIT{1'b0}};
		        else
				real_inc = reg_increment_n ;	
		end
		else begin
			// we don't decrement if reg_count is at zero
			if (count_all_zeros == 1'b1)
				real_dec = {INC_DEC_BIT{1'b0}};
			else
				real_dec = reg_decrement_n ;
		end

		// counter
		if (err_detected) // If there is an error we increment the register
			reg_count_q = reg_count_n + real_inc;
		else
			reg_count_q = reg_count_n - real_dec;

		if ( reg_count_q > reg_threshold_n )
			is_broken = 1'b1;
       		else
			is_broken = 1'b0;
			
		// broken selections
		if (reg_is_broken_n == 1'b1)
			is_broken_o = 1'b1;
       		else
			is_broken_o = is_broken;

		if (set_broken_i == 1'b1)
			reg_is_broken_q = 1'b1;
		else
			reg_is_broken_q = is_broken_o;

	end
  	
	cv32e40p_clock_gate clock_gated
        (
         .clk_i        ( clk ),
         .en_i         ( ~reg_is_broken_n ),
         .scan_cg_en_i ( 1'b0 ), // not used 
         .clk_o        ( clk_gated )
        );

endmodule
