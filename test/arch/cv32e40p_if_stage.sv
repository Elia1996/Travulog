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
// Engineer:       Renzo Andri - andrire@student.ethz.ch                      //
//                                                                            //
// Additional contributions by:                                               //
//                 Igor Loi - igor.loi@unibo.it                               //
//                 Andreas Traber - atraber@student.ethz.ch                   //
//                 Sven Stucki - svstucki@student.ethz.ch                     //
//                                                                            //
// Design Name:    Instruction Fetch Stage                                    //
// Project Name:   RI5CY                                                      //
// Language:       SystemVerilog                                              //
//                                                                            //
// Description:    Instruction fetch unit: Selection of the next PC, and      //
//                 buffering (sampling) of the read instruction               //
//                                                                            //
/////////////////////////////////////////////////////////////////////////////////


//// IMPORT htv_pkg.tv

import cv32e40p_pkg::*;
//// ADD_LINE import cv32e40p_pkg2::*;


//// NEW_MODULE_NAME cv32e40p_if_stage
//// NEW_MODULE_FILE OUT_DIR/cv32e40p_if_stage_ft.sv

module cv32e40p_if_stage
#(
  parameter PULP_XPULP      = 0,                        // PULP ISA Extension (including PULP specific CSRs and hardware loop, excluding p.elw)
  parameter PULP_OBI        = 0,                        // Legacy PULP OBI behavior
  parameter PULP_SECURE     = 0,
  parameter FPU             = 0
)
(
	input  logic        clk,
	input  logic        rst_n,

	// Used to calculate the exception offsets
	input  logic [23:0] m_trap_base_addr_i, // cs_registers_i
	input  logic [23:0] u_trap_base_addr_i, // cs_registers_i
	input  logic  [1:0] trap_addr_mux_i, // id_stage_i
	// Boot address
	input  logic [31:0] boot_addr_i, // core in 
	input  logic [31:0] dm_exception_addr_i, // core in

	// Debug mode halt address
	input  logic [31:0] dm_halt_addr_i, // core in

	// instruction request control
	input  logic        req_i, // id_stage_i

	// instruction cache interface
	output logic                   instr_req_o, 
	output logic            [31:0] instr_addr_o,
	input  logic                   instr_gnt_i, // pmp_unit_i
	input  logic                   instr_rvalid_i,  // core in
	input  logic            [31:0] instr_rdata_i, // core in
	input  logic                   instr_err_i,   // 0 fisso  // External bus error (validity defined by instr_rvalid_i) (not used yet)
	input  logic                   instr_err_pmp_i, // pmp_unit_i // PMP error (validity defined by instr_gnt_i)

	// Output of IF Pipeline stage
	output logic              instr_valid_id_o,      // instruction in IF/ID pipeline is valid
	output logic       [31:0] instr_rdata_id_o,      // read instruction is sampled and sent to ID stage for decoding
	output logic              is_compressed_id_o,    // compressed decoder thinks this is a compressed instruction
	output logic              illegal_c_insn_id_o,   // compressed decoder thinks this is an invalid instruction
	output logic       [31:0] pc_if_o,
	output logic       [31:0] pc_id_o,
	output logic              is_fetch_failed_o,

	// Forwarding ports - control signals
	input  logic        clear_instr_valid_i,   // clear instruction valid bit in IF/ID pipe (id_stage_i)
	input  logic        pc_set_i,              // set the program counter to a new value (id_stage_i)
	input  logic [31:0] mepc_i,                // address used to restore PC when the interrupt/exception is served (cs_registers_i)
	input  logic [31:0] uepc_i,                // address used to restore PC when the interrupt/exception is served (cs_registers_i)

	input  logic [31:0] depc_i,                // address used to restore PC when the debug is served (cs_registers_i)

	input  logic  [3:0] pc_mux_i,              // sel for pc multiplexer (id_stage_i)
	input  logic  [2:0] exc_pc_mux_i,          // selects ISR address (id_stage_i)

	input  logic  [4:0] m_exc_vec_pc_mux_i,    // selects ISR address for vectorized interrupt lines (id_stage_i e core)
	input  logic  [4:0] u_exc_vec_pc_mux_i,    // selects ISR address for vectorized interrupt lines (id_stage_i e core)
	output logic        csr_mtvec_init_o,      // tell CS regfile to init mtvec (id_stage_i)

	// jump and branch target and decision
	input  logic [31:0] jump_target_id_i,      // jump target address (id_stage_i)
	input  logic [31:0] jump_target_ex_i,      // jump target address (ex_stage_i)

	// from hwloop controller
	input  logic        hwlp_jump_i, // id_stage_i
	input  logic [31:0] hwlp_target_i, //id_stage_i

	// pipeline stall
	input  logic        halt_if_i, // id_stage_i
	input  logic        id_ready_i, // id_stage_i

	// misc signals
	output logic        if_busy_o,             // is the IF stage busy fetching instructions?
	output logic        perf_imiss_o           // Instruction Fetch Miss
);

	logic              if_valid, if_ready;

	// prefetch buffer related signals
	logic              prefetch_busy;
	logic              branch_req;
	logic       [31:0] branch_addr_n;

	logic              fetch_valid;
	logic              fetch_ready;
	logic       [31:0] fetch_rdata;

	logic       [31:0] exc_pc;

	logic [23:0]       trap_base_addr;
	logic  [4:0]       exc_vec_pc_mux;
	logic              fetch_failed;

	logic              aligner_ready;
	logic              instr_valid;

	logic              illegal_c_insn;
	logic [31:0]       instr_aligned;
	logic [31:0]       instr_decompressed;
	logic              instr_compressed_int;


	assign if_busy_o       = prefetch_busy;
	assign fetch_failed    = 1'b0; // PMP is not supported in CV32E40P
	
	//// FOREACH MAIN_MOD_INTERN
	////    logic [2:0]BITINIT SIGNAME_tr;
	//// END_FOREACH
	
	//// FOREACH MAIN_MOD_OUT NOT if_busy_o
	//// 	logic [2:0]BITINIT SIGNAME_tr;
	//// END_FOREACH

 	//// FOREACH MAIN_MOD_OUT NOT if_busy_o
	//// 	assign SIGNAME = SIGNAME_tr[0];
	//// END_FOREACH
	
	//// FOREACH NEW_OUT
	//// 	logic [5:0]BITINIT SIGNAME_ft;
	//// END_FOREACH
	
	//// FOREACH NEW_IN NOT clk rst_n
	//// 	logic [5:0]BITINIT SIGNAME_ft;
	//// 	assign SIGNAME_ft = {3'b0, 3'b0, 3'b0, 3'b0, 3'b0, 3'b0};
	//// END_FOREACH
	
	//// FOREACH prefetch_busy 
	//// 	assign if_busy_o = SIGNAME_tr[0];
	//// END_FOREACH
	
	//// FOREACH fetch_failed
	////	assign SIGNAME_tr = {1'b0, 1'b0, 1'b0};
	//// END_FOREACH
	

	
	////////////////////////////////////////////////////////////
	//// END_DECLARATIONS
	///////////////////////////////////////////////////////////

	//// ADD_MODULE_LAYER 
	//// TEMPLATE ft_template
	//// INFILE OUT_DIR/cv32e40p_program_counter_definition.sv
	//// OUTFILE OUT_DIR/cv32e40p_program_counter_definition_ft.sv
	////
	//// CONNECT  IF clk rst_n IN = IN
	////          IF MAIN_MOD_IN IN = {IN , IN , IN }
	////          IF NEW_IN IN = IN_ft[MAIN_MOD_ID_CURRENT_MOD_ID] 
	////	      IN = IN_tr
	////	      IF NEW_OUT OUT = OUT_ft[MAIN_MOD_ID_CURRENT_MOD_ID]
	//// 	      OUT = OUT_tr	
	//// END_CONNECT

	////	 CREATE_MODULE cv32e40p_program_counter_definition
	////	 OUTFILE OUT_DIR/cv32e40p_program_counter_definition.sv
	////	
	////	 IN m_exc_vec_pc_mux_i 
	////	    u_exc_vec_pc_mux_i
	////	    trap_addr_mux_i 
	////	    exc_pc_mux_i
	////	    dm_halt_addr_i 
	////	    m_trap_base_addr_i u_trap_base_addr_i 
	////	 	  boot_addr_i
	////	    dm_exception_addr_i
	////	    jump_target_id_i
	////	    jump_target_ex_i
	////	    mepc_i uepc_i depc_i pc_id_o 
	////	    hwlp_target_i
	////	    pc_set_i pc_mux_i
	////	 END_IN
	////	 OUT branch_addr_n
	////	    csr_mtvec_init_o
	////	 END_OUT
	
	// exception PC selection mux
	always_comb
		begin : EXC_PC_MUX
			unique case (trap_addr_mux_i)
				TRAP_MACHINE:  trap_base_addr = m_trap_base_addr_i;
				TRAP_USER:     trap_base_addr = u_trap_base_addr_i;
			default:       trap_base_addr = m_trap_base_addr_i;
		endcase

		unique case (trap_addr_mux_i)
			TRAP_MACHINE:  exc_vec_pc_mux = m_exc_vec_pc_mux_i;
			TRAP_USER:     exc_vec_pc_mux = u_exc_vec_pc_mux_i;
			default:       exc_vec_pc_mux = m_exc_vec_pc_mux_i;
		endcase

		unique case (exc_pc_mux_i)
			EXC_PC_EXCEPTION:                        exc_pc = { trap_base_addr, 8'h0 }; //1.10 all the exceptions go to base address
			EXC_PC_IRQ:                              exc_pc = { trap_base_addr, 1'b0, exc_vec_pc_mux, 2'b0 }; // interrupts are vectored
			EXC_PC_DBD:                              exc_pc = { dm_halt_addr_i[31:2], 2'b0 };
			EXC_PC_DBE:                              exc_pc = { dm_exception_addr_i[31:2], 2'b0 };
			default:                                 exc_pc = { trap_base_addr, 8'h0 };
		endcase
	end

	// fetch address selection
	always_comb
		begin
		// Default assign PC_BOOT (should be overwritten in below case)
		branch_addr_n = {boot_addr_i[31:2], 2'b0};

		unique case (pc_mux_i)
			PC_BOOT:      branch_addr_n = {boot_addr_i[31:2], 2'b0};
			PC_JUMP:      branch_addr_n = jump_target_id_i;
			PC_BRANCH:    branch_addr_n = jump_target_ex_i;
			PC_EXCEPTION: branch_addr_n = exc_pc;             // set PC to exception handler
			PC_MRET:      branch_addr_n = mepc_i; // PC is restored when returning from IRQ/exception
			PC_URET:      branch_addr_n = uepc_i; // PC is restored when returning from IRQ/exception
			PC_DRET:      branch_addr_n = depc_i; //
			PC_FENCEI:    branch_addr_n = pc_id_o + 4; // jump to next instr forces prefetch buffer reload
			PC_HWLOOP:    branch_addr_n = hwlp_target_i;
			default:;
		endcase
	end

	// tell CS register file to initialize mtvec on boot
	assign csr_mtvec_init_o = (pc_mux_i == PC_BOOT) & pc_set_i;

	//// 	END_CREATE_MODULE
	//// END_ADD_MODULE_LAYER


	// prefetch buffer, caches a fixed number of instructions
	
	//// ADD_MODULE_LAYER 
	//// TEMPLATE ft_template 
	//// INFILE IN_DIR/cv32e40p_prefetch_buffer.sv
	//// OUTFILE OUT_DIR/cv32e40p_prefetch_buffer_ft.sv
	////
	//// CONNECT  IF clk rst_n IN = IN
	////	      IF branch_addr_n IN = {IN_tr[2] , IN_tr[1] , IN_tr[0] }
	////	      IF MAIN_MOD_IN IN = {IN , IN , IN }
	////          IF NEW_IN IN = IN_ft[MAIN_MOD_ID_CURRENT_MOD_ID] 
	////	      IN = IN_tr
	////	      IF NEW_OUT OUT = OUT_ft[MAIN_MOD_ID_CURRENT_MOD_ID]
	//// 	      OUT = OUT_tr	
	//// END_CONNECT
	cv32e40p_prefetch_buffer
	#(
		.PULP_OBI          ( PULP_OBI                    ),
		.PULP_XPULP        ( PULP_XPULP                  )
	) 
	prefetch_buffer_i
	(
		.clk               ( clk                         ),
		.rst_n             ( rst_n                       ),

		.req_i             ( req_i                       ),

		.branch_i          ( branch_req                  ),
		.branch_addr_i     ( {branch_addr_n[31:1], 1'b0} ),

		.hwlp_jump_i       ( hwlp_jump_i                 ),
		.hwlp_target_i     ( hwlp_target_i               ),

		.fetch_ready_i     ( fetch_ready                 ),
		.fetch_valid_o     ( fetch_valid                 ),
		.fetch_rdata_o     ( fetch_rdata                 ),

		// goes to instruction memory / instruction cache
		.instr_req_o       ( instr_req_o                 ),
		.instr_addr_o      ( instr_addr_o                ),
		.instr_gnt_i       ( instr_gnt_i                 ),
		.instr_rvalid_i    ( instr_rvalid_i              ),
		.instr_err_i       ( instr_err_i                 ),     // Not supported (yet)
		.instr_err_pmp_i   ( instr_err_pmp_i             ),     // Not supported (yet)
		.instr_rdata_i     ( instr_rdata_i               ),

		// Prefetch Buffer Status
		.busy_o            ( prefetch_busy               )
	);
	//// END_ADD_MODULE_LAYER


	//// ADD_MODULE_LAYER 
	//// TEMPLATE ft_template 
	//// INFILE OUT_DIR/cv32e40p_if_stage_fsm_logic.sv
	//// OUTFILE OUT_DIR/cv32e40p_if_stage_fsm_logic_ft.sv
	////
	//// CONNECT  IF clk rst_n IN = IN
	////	      IF MAIN_MOD_IN IN = {IN , IN , IN }
	////          IF NEW_IN IN = IN_ft[MAIN_MOD_ID_CURRENT_MOD_ID] 
	////	      IN = IN_tr
	////	      IF NEW_OUT OUT = OUT_ft[MAIN_MOD_ID_CURRENT_MOD_ID]
	//// 	      OUT = OUT_tr	
	//// END_CONNECT
	
	////	 CREATE_MODULE cv32e40p_if_stage_fsm_logic
	////	 OUTFILE OUT_DIR/cv32e40p_if_stage_fsm_logic.sv
	////	
	////	 IN pc_set_i
	////	    fetch_valid
	////	    req_i
	////	    if_valid
	////	    aligner_ready
	////	 END_IN
	////	 OUT branch_req
	////	 	   fetch_ready
	////	     perf_imiss_o
	////	 END_OUT

	// offset FSM state transition logic
	always_comb
		begin

		fetch_ready   = 1'b0;
		branch_req    = 1'b0;
		// take care of jumps and branches
		if (pc_set_i) begin
			branch_req    = 1'b1;
		end
		else if (fetch_valid) begin
			if (req_i && if_valid) begin
				fetch_ready   = aligner_ready;
			end
		end
	end

	assign perf_imiss_o    = (~fetch_valid) | branch_req;
	////	 END_CREATE_MODULE
	//// END_ADD_MODULE_LAYER


	//// ADD_MODULE_LAYER 
	//// TEMPLATE ft_template 
	//// INFILE OUT_DIR/cv32e40p_if_pipeline.sv
	//// OUTFILE OUT_DIR/cv32e40p_if_pipeline_ft.sv
	////
	//// CONNECT  IF clk rst_n IN = IN
	////	      IF MAIN_MOD_IN IN = {IN , IN , IN }
	////          IF NEW_IN IN = IN_ft[MAIN_MOD_ID_CURRENT_MOD_ID] 
	////	      IN = IN_tr
	////	      IF NEW_OUT OUT = OUT_ft[MAIN_MOD_ID_CURRENT_MOD_ID]
	//// 	      OUT = OUT_tr	
	//// END_CONNECT
	
	//// CREATE_MODULE cv32e40p_if_pipeline 
	//// OUTFILE OUT_DIR/cv32e40p_if_pipeline.sv
	////
	//// IN rst_n
	////    instr_decompressed
	////    instr_compressed_int
	////    pc_if_o
	////    fetch_failed
	////    id_ready_i
	////    halt_if_i
	////    instr_valid
	////    clear_instr_valid_i
	////    illegal_c_insn
	////    fetch_valid
	////    clk
	//// END_IN
	//// OUT instr_valid_id_o
	////     instr_rdata_id_o
	////     is_fetch_failed_o
	////     pc_id_o
	////     is_compressed_id_o
	////     illegal_c_insn_id_o
	////     if_valid
	//// END_OUT


	// IF-ID pipeline registers, frozen when the ID stage is stalled
	always_ff @(posedge clk, negedge rst_n)
		begin : IF_ID_PIPE_REGISTERS
		if (rst_n == 1'b0)
			begin
			instr_valid_id_o      <= 1'b0;
			instr_rdata_id_o      <= '0;
			is_fetch_failed_o     <= 1'b0;
			pc_id_o               <= '0;
			is_compressed_id_o    <= 1'b0;
			illegal_c_insn_id_o   <= 1'b0;
		end
		else
			begin

			if (if_valid && instr_valid)
				begin
				instr_valid_id_o    <= 1'b1;
				instr_rdata_id_o    <= instr_decompressed;
				is_compressed_id_o  <= instr_compressed_int;
				illegal_c_insn_id_o <= illegal_c_insn;
				is_fetch_failed_o   <= 1'b0;
				pc_id_o             <= pc_if_o;
			end else if (clear_instr_valid_i) begin
				instr_valid_id_o    <= 1'b0;
				is_fetch_failed_o   <= fetch_failed;
			end
		end
	end

	assign if_ready = fetch_valid & id_ready_i;
	assign if_valid = (~halt_if_i) & if_ready;

	//// END_CREATE_MODULE
	//// END_ADD_MODULE_LAYER


	//// ADD_MODULE_LAYER 
	//// TEMPLATE ft_template 
	//// INFILE IN_DIR/cv32e40p_aligner.sv
	//// OUTFILE OUT_DIR/cv32e40p_aligner_ft.sv
	////
	//// CONNECT  IF clk rst_n IN = IN
	////	      IF branch_addr_n IN = {IN_tr[2] ,IN_tr[1], IN_tr[0]}
	//// 	      IF NEW_IN IN = IN_ft[MAIN_MOD_ID_CURRENT_MOD_ID]
	////	      IF MAIN_MOD_IN IN = {IN , IN , IN }
	////	      IF NEW_IN IN = IN_tr
	////	      IN = IN_tr
	////	      IF NEW_OUT OUT = OUT_ft[MAIN_MOD_ID_CURRENT_MOD_ID]
	//// 	      OUT = OUT_tr	
	//// END_CONNECT
	cv32e40p_aligner aligner_i
	(
		.clk               ( clk                          ),
		.rst_n             ( rst_n                        ),
		.fetch_valid_i     ( fetch_valid                  ),
		.aligner_ready_o   ( aligner_ready                ),
		.if_valid_i        ( if_valid                     ),
		.fetch_rdata_i     ( fetch_rdata                  ),
		.instr_aligned_o   ( instr_aligned                ),
		.instr_valid_o     ( instr_valid                  ),
		.branch_addr_i     ( {branch_addr_n[31:1], 1'b0}  ),
		.branch_i          ( branch_req                   ),
		.hwlp_addr_i       ( hwlp_target_i                ),
		.hwlp_update_pc_i  ( hwlp_jump_i                  ),
		.pc_o              ( pc_if_o                      )
	);

	//// END_ADD_MODULE_LAYER

	//// ADD_MODULE_LAYER 
	//// TEMPLATE ft_template 
	//// INFILE IN_DIR/cv32e40p_compressed_decoder.sv
	//// OUTFILE OUT_DIR/cv32e40p_compressed_decoder_ft.sv
	////
	//// CONNECT  IF clk rst_n IN = IN
	////	      IF NEW_IN IN = IN_ft[MAIN_MOD_ID_CURRENT_MOD_ID]
	////	      IF MAIN_MOD_IN IN = {IN , IN , IN }
	////	      IN = IN_tr
	////	      IF NEW_OUT OUT = OUT_ft[MAIN_MOD_ID_CURRENT_MOD_ID]
	//// 	      OUT = OUT_tr	
	//// END_CONNECT
	cv32e40p_compressed_decoder
	#(
		.FPU(FPU)
	)
	compressed_decoder_i
	(
		.clk(clk),
		.rst_n(rst_n),
		.instr_i         ( instr_aligned        ),
		.instr_o         ( instr_decompressed   ),
		.is_compressed_o ( instr_compressed_int ),
		.illegal_instr_o ( illegal_c_insn       )
	);	
	//// END_ADD_MODULE_LAYER

	//----------------------------------------------------------------------------
	// Assertions
	//----------------------------------------------------------------------------

`ifdef CV32E40P_ASSERT_ON

  generate
  if (!PULP_XPULP) begin

    // Check that PC Mux cannot select Hardware Loop address iF PULP extensions are not included
    property p_pc_mux_0;
       @(posedge clk) disable iff (!rst_n) (1'b1) |-> (pc_mux_i != PC_HWLOOP);
    endproperty

    a_pc_mux_0 : assert property(p_pc_mux_0);

  end
  endgenerate

 generate
  if (!PULP_SECURE) begin

    // Check that PC Mux cannot select URET address if User Mode is not included
    property p_pc_mux_1;
       @(posedge clk) disable iff (!rst_n) (1'b1) |-> (pc_mux_i != PC_URET);
    endproperty

    a_pc_mux_1 : assert property(p_pc_mux_1);

  end
  endgenerate

`endif

endmodule
