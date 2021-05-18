	//////////////////////////////////////////////////////////////////////
	// MODULE_NAME_ft	
	//////////////////////////////////////////////////////////////////////
	parameter int PARAM_NAME_FT = 1;
	parameter int PARAM_NAME_TIN = 0;
        // TOUT is referred to output signal in order of definition
        //
        // OP_FOREACH BLOCK OUT // TOUT[INDEX]-refers-to->>SIGNAME
	parameter int PARAM_NAME_TOUT [SIG_NUM-BLOCK-OUT:0] = { OP_FOREACH BLOCK OUT , 0  };

	// Parameter for breakage monitors
	parameter PARAM_NAME_DECREMENT = 1; 
	parameter PARAM_NAME_INCREMENT = 1; 
	parameter PARAM_NAME_BREAKING_THRESHOLD = 3; 
	parameter PARAM_NAME_COUNT_BIT = 8; 
	parameter PARAM_NAME_INC_DEC_BIT = 2; 

	parameter MAIN_MOD_ID_CURRENT_MOD_ID = MODULE_ORDER;

	
