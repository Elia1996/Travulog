#!/usr/bin/python3

from moddata import *
from travulog import *
from htravulog import *
import json

DIR="/media/tesla/Storage/Data/Scrivania/AllProject/Fare/Tesi/Esecuzione_tesi/"


main_mod_name = "cv32e40p_if_stage.sv"
input_dir = DIR + "/cv32e40p_ft_tests/FTGenerator/test/arch/"
output_dir = DIR + "/cv32e40p_ft_tests/FTGenerator/out"
templates_dir = DIR+"cv32e40p_ft_tests/FTGenerator/templates/"
template_fname_dict = {"ft_template" : templates_dir+"ft_template.sv"}
template_parameters_filename_dict = {"ft_template" : templates_dir+"ft_template_parameters.sv"}
package_template_filename = templates_dir+"cv32e40p_pkg2.sv"
module_prefix = "cv32e40p_"
indent = "        "

main_mod_obj = htravulog(input_dir, main_mod_name, output_dir, template_fname_dict, template_parameters_filename_dict, package_template_filename, module_prefix, indent)

main_mod_obj.ElaborateHiddenTravulog()
