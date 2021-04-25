module cv32e40p_program_counter_definition
(
        input  logic             [4:0]  m_exc_vec_pc_mux_i ,
        input  logic             [4:0]  u_exc_vec_pc_mux_i ,
        input  logic             [1:0]  trap_addr_mux_i ,
        input  logic             [2:0]  exc_pc_mux_i ,
        input  logic            [31:0]  dm_halt_addr_i ,
        input  logic            [23:0]  m_trap_base_addr_i ,
        input  logic            [23:0]  u_trap_base_addr_i ,
        input  logic            [31:0]  boot_addr_i ,
        input  logic            [31:0]  dm_exception_addr_i ,
        input  logic            [31:0]  jump_target_id_i ,
        input  logic            [31:0]  jump_target_ex_i ,
        input  logic            [31:0]  mepc_i ,
        input  logic            [31:0]  uepc_i ,
        input  logic            [31:0]  depc_i ,
        input  logic            [31:0]  pc_id_o ,
        input  logic            [31:0]  hwlp_target_i ,
        input  logic                    pc_set_i ,
        input  logic             [3:0]  pc_mux_i ,
        output logic            [31:0]  branch_addr_n ,
        output logic                    csr_mtvec_init_o 
)
        logic            [31:0]  exc_pc ;
        logic            [23:0]  trap_base_addr ;
        logic             [4:0]  exc_vec_pc_mux ;


        always_comb                begin : EXC_PC_MUX
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

endmodule
