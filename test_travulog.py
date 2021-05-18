#!/usr/bin/python3

from travulog import *


template_fname = "templates/ft_template.sv"
template_params_fname = "templates/ft_template_parameters.sv"
module_fname_dict = {"BLOCK" : "./test/arch/cv32e40p_compressed_decoder.sv"}
module_prefix = "cv32e40p_"

tr = travulog(template_fname, template_params_fname, module_fname_dict, module_prefix)

print(tr.GetElaboratedTemplate("ciccio","CIC"))
