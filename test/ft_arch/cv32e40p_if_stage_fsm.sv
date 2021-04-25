module cv32e40p_if_stage_fsm
(
        input  logic                    pc_set_i ,
        input  logic                    fetch_valid ,
        input  logic                    req_i ,
        input  logic                    if_valid ,
        input  logic                    aligner_ready ,
        output logic                    branch_req ,
        output logic                    fetch_ready ,
        output logic                    perf_imiss_o 
)


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

endmodule
