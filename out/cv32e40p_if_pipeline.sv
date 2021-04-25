import cv32e40p_pkg::*;



module cv32e40p_if_pipeline
(
        input  logic                    rst_n ,
        input  logic            [31:0]  instr_decompressed ,
        input  logic                    instr_compressed_int ,
        input  logic            [31:0]  pc_if_o ,
        input  logic                    fetch_failed ,
        input  logic                    id_ready_i ,
        input  logic                    halt_if_i ,
        input  logic                    instr_valid ,
        input  logic                    clear_instr_valid_i ,
        input  logic                    illegal_c_insn ,
        input  logic                    fetch_valid ,
        input  logic                    clk ,
        output logic                    instr_valid_id_o ,
        output logic            [31:0]  instr_rdata_id_o ,
        output logic                    is_fetch_failed_o ,
        output logic            [31:0]  pc_id_o ,
        output logic                    is_compressed_id_o ,
        output logic                    illegal_c_insn_id_o ,
        output logic                    if_valid 
);
        logic                    if_ready ;



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

endmodule
