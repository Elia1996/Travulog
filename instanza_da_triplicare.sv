  cv32e40p_if_stage
  #(
    .PULP_XPULP          ( PULP_XPULP        ),
    .PULP_OBI            ( PULP_OBI          ),
    .PULP_SECURE         ( PULP_SECURE       ),
    .FPU                 ( FPU               )
  )
  if_stage_i
  (
    .clk                 ( clk               ),
    .rst_n               ( rst_ni            ),

    // boot address
    .boot_addr_i         ( boot_addr_i[31:0] ),
    .dm_exception_addr_i ( dm_exception_addr_i[31:0] ),

    // debug mode halt address
    .dm_halt_addr_i      ( dm_halt_addr_i[31:0] ),

    // trap vector location
    .m_trap_base_addr_i  ( mtvec             ),
    .u_trap_base_addr_i  ( utvec             ),
    .trap_addr_mux_i     ( trap_addr_mux     ),

    // instruction request control
    .req_i               ( instr_req_int     ),

    // instruction cache interface
    .instr_req_o         ( instr_req_pmp     ),
    .instr_addr_o        ( instr_addr_pmp    ),
    .instr_gnt_i         ( instr_gnt_pmp     ),
    .instr_rvalid_i      ( instr_rvalid_i    ),
    .instr_rdata_i       ( instr_rdata_i     ),
    .instr_err_i         ( 1'b0              ),  // Bus error (not used yet)
    .instr_err_pmp_i     ( instr_err_pmp     ),  // PMP error

    // outputs to ID stage
    .instr_valid_id_o    ( instr_valid_id    ),
    .instr_rdata_id_o    ( instr_rdata_id    ),
    .is_fetch_failed_o   ( is_fetch_failed_id ),

    // control signals
    .clear_instr_valid_i ( clear_instr_valid ),
    .pc_set_i            ( pc_set            ),

    .mepc_i              ( mepc              ), // exception return address
    .uepc_i              ( uepc              ), // exception return address

    .depc_i              ( depc              ), // debug return address

    .pc_mux_i            ( pc_mux_id         ), // sel for pc multiplexer
    .exc_pc_mux_i        ( exc_pc_mux_id     ),


    .pc_id_o             ( pc_id             ),
    .pc_if_o             ( pc_if             ),

    .is_compressed_id_o  ( is_compressed_id  ),
    .illegal_c_insn_id_o ( illegal_c_insn_id ),

    .m_exc_vec_pc_mux_i  ( m_exc_vec_pc_mux_id ),
    .u_exc_vec_pc_mux_i  ( u_exc_vec_pc_mux_id ),

    .csr_mtvec_init_o    ( csr_mtvec_init    ),

    // from hwloop registers
    .hwlp_jump_i         ( hwlp_jump         ),
    .hwlp_target_i       ( hwlp_target       ),


    // Jump targets
    .jump_target_id_i    ( jump_target_id    ),
    .jump_target_ex_i    ( jump_target_ex    ),

    // pipeline stalls
    .halt_if_i           ( halt_if           ),
    .id_ready_i          ( id_ready          ),

    .if_busy_o           ( if_busy           ),
    .perf_imiss_o        ( perf_imiss        )
  );

