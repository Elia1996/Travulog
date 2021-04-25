#!/usr/bin/python3
import sys
import os
import re
import json
from pathlib import Path
import shutil

from moddata import *
from travulog import *

#  CompressLineSpaceTabs(line):
#  CompressInstanceLine(line):
#  SplitInstanceLine(line):
#  htravulog class
#     __init__(sf, input_dir, htravulog_filename, output_dir, template_filename_dict, template_parameters_filename_dict,\
#     CreateNewBlockInfo(sf, cmd_dict):
#     CreateFtBlock(sf, cmd_dict, indent):
#     BlockToFT(sf,cmd_dict, indent_int):
#     CreateAndSaveFtBlock(sf, md_obj, template_name, block_name, ft_sig_index, ft_sig_no_index_list):
#     GetFtSignalIndex(sf, block_name):
#     ElaborateHiddenTravulog(sf):
#           Questa funzione analizza un file con del codice travulog nascosto e genera i blocchi
#           necessari, crea le instanze e modifica quelle già presenti in base ai comandi travulog nascosti


def CompressLineSpaceTabs(line):
    return " ".join(line.strip().split()).strip()

def CompressInstanceLine(line):
    line_no_space = CompressLineSpaceTabs(line)
    line1 = line_no_space.replace(".", " ").replace("(","#")
    line2 = re.sub(r'\)\W*,' , ' ' , line1)
    line2 = re.sub(r'\)\W*\)*' , ' ' , line2)
    line3 = RemoveComments(line2)
    line3 = line3.replace(" # ", "#")
    line_compress = CompressLineSpaceTabs(line3)
    return line_compress 

def SplitInstanceLine(line):
    return CompressInstanceLine(line).split("#")


class htravulog:
    def __init__(sf, input_dir, htravulog_filename, output_dir, template_filename_dict, template_parameters_filename_dict,\
                                                    package_template_filename, module_prefix="", indent="        "):
        """
        htravulog_filename -> filename of the verilog file with htravulog code
        ft_output_dir -> directory where transformed file will be placed
        template_filename_dict -> dictionary of template that can be used inside htravulof, the key of the 
                dictionary is the string used in htravulog to indicate the template, the value is the absolute
                filename of the template written in verilog with travulog
                {"ft_template" : path/ft_template.sv , "ft_templateECC" : path/ft_templateECC1.sv}
        template_parameters_filename_dict -> as template_filename_dict but for the parameter templates
                {"ft_template" : path/ft_template_params.sv , "ft_templateECC" : path/ft_templateECC_params.sv}
        package_filename -> dictionary of package associate to relative template, the key is the same, if the value
                is a empty string the package doesn't exist, otherwise are used
        """
        sf.htravulog_filename = input_dir + "/" + htravulog_filename
        sf.input_dir = input_dir
        os.chdir(sf.input_dir)
        sf.md_main_block_obj = moddata(sf.htravulog_filename, module_prefix, indent)
        sf.md_main_block_obj.Analyze()

        sf.output_dir = output_dir
        sf.indent=indent
        sf.module_prefix = module_prefix
        sf.template_params_datafile = ""
        sf.package_filename = package_template_filename
        
        if len(template_filename_dict)!= len(template_parameters_filename_dict):
            print("ERROR in htravulog init, template_filename_dict and package_filename_dict should have same lenght")
            exit(-1)

        sf.tv_template_obj = {}

        for key, template_filename, template_parameters_filename in \
                zip(template_filename_dict.keys(), template_filename_dict.values(), template_parameters_filename_dict.values()): 
            sf.tv_template_obj[key] = travulog(template_filename, template_parameters_filename, {}, module_prefix, indent)

        sf.HTKEY="////"

    def CreateNewBlockInfo(sf, cmd_dict):
        """ Return a moddata object rapresent the new block
        This function use the info from sf.md_main_blocks_obj (that contain 
        moddata object of the htravulog file that we are analyzing) in order to 
        find the property of the signal of the new block. 

        cmd_dict["IN"] and cmd_dict["OUT"] are input/output signals of new block
        , these signal are already defined in the main block as input/output or intern
        signals, using the main block definition we find the bits of each signals and store
        it. This operation is done with SetSigAsAnotherModuleSig function of the new moddata object created.
        The new block isn't already fault tolerant, the transformation is done using 
        the ft template in another function.
        cmd_dict should also contain the name of the new block as "block_name"
        """
        cmd_in_sig = cmd_dict["IN"]
        cmd_out_sig = cmd_dict["OUT"]

        new_block_obj = moddata("", sf.module_prefix, sf.indent)
        new_block_obj.SetVerilogBlock(cmd_dict["verilog_block"])
        new_block_obj.SetModuleName(cmd_dict["block_name"])
        new_block_obj.SetImportList(sf.md_main_block_obj.GetImportList())

        #print(cmd_in_sig)
        #print(sf.md_main_block_obj.GetInputSigNamesList())
        IN = sf.md_main_block_obj.IN_ID
        if new_block_obj.SetSigAsAnotherModuleSig(sf.md_main_block_obj, cmd_in_sig, IN ) == 1:
            print("ERROR in CreateNewBlockInfo, input signal of %d block aren't in main block %s" % \
                    (cmd_dict["block_name"], sf.md_main_block_obj.GetModuleName()))

        OUT = sf.md_main_block_obj.OUT_ID
        if new_block_obj.SetSigAsAnotherModuleSig(sf.md_main_block_obj, cmd_out_sig, OUT) == 1:
            print("ERROR in CreateNewBlockInfo, output signal of %d block aren't in main block %s" % \
                    (cmd_dict["block_name"], sf.md_main_block_obj.GetModuleName()))
        
        new_block_obj.SetInternSigFromOtherModuleSearchingInVerilogCode(sf.md_main_block_obj)
        
        return new_block_obj



    def CreateFtBlock(sf, cmd_dict, indent):
        """ Return new block instance
        This function create a new block form a part of a verilog file:
        cmd_dict -> contain the command dictionary with follow info:
                    {"template" : template_short_name_used_inside_htravulog_code,
                    "block_name" : name_of_the_new_block_setted_in_htravulog,
                    "IN" : [ input_signals_list_of_the_new_code ],
                    "OUT" : [ input_signals_list_of_the_new_code ],
                    "verilog_block" : verilog_code_of_the_new_block ,
                    "ft_signal_index" : index_of_ft_signals_used_for_instance_connection,
                    "ft_signal_no_index_list" : list_of_ft_signal_for_which_avoid_to_add_index}
        """
     
        filename = sf.output_dir+"/"+cmd_dict["block_name"]+".sv"
        ft_filename = sf.output_dir+"/"+cmd_dict["block_name"]+"_ft.sv"
        
        # We create  a new moddata object of the new block 
        md_newmod_obj = sf.CreateNewBlockInfo(cmd_dict)

        ##### DATAFILE CREATION
        datafile = md_newmod_obj.GetCompleteVerilog()
        #print(datafile.split("\n")[0])
        if datafile == "":
            print("ERROR in CreateFtBlock, GetCompleteVerilog return empty string")
            exit(-1)

        # We print datafile on file (not already ft)
        fp = open(filename,"w")
        fp.write(datafile)
        fp.close()

        ##### FT block creation
        #### FT block creation and saving
        md_ft_module_obj = sf.CreateAndSaveFtBlock( md_newmod_obj, \
                                                    cmd_dict["template"], \
                                                    cmd_dict["block_name"], \
                                                    cmd_dict["ft_signal_index"], \
                                                    cmd_dict["ft_signal_no_index_list"]) 
        

        
        instance_name = md_ft_module_obj.GetModuleNameNoPrefix()


        #### Create instance
        instance = md_ft_module_obj.GetInstance( instance_name, indent)
        
        #### Set new internal sig in the global variable
        sf.FindAndSetInternSigDictFromInstance(md_ft_module_obj)
       
        return instance

    def BlockToFT(sf,cmd_dict, indent_int):
        """ Return the ft block instance 
        cmd_dict should contain:
                 {"template"         : "template_short_name_used_inside_htravulog_code",
                  "block_name"       : "name_of_the_new_block_setted_in_htravulog",
                  "param_dict"  : [list_of_dict_of_parameter_connections],
                  "io_dict"     : [list_of_dict_of_io_connections],
                  "module_filename"  : "filename of the module to become ft",
                  "instance_name"    : "name of the instance" 
                  }
        indent_int -> number of tab of indentation 
        """
        ##### Creation of block object
        
        md_mod_obj = moddata(cmd_dict["module_filename"], sf.module_prefix, sf.indent)
        md_mod_obj.Analyze()


        #### FT block creation, saving, find diff signals and add to connection ports
        md_ft_module_obj = sf.CreateAndSaveFtBlock( md_mod_obj, \
                                                    cmd_dict["template"], \
                                                    cmd_dict["block_name"], \
                                                    cmd_dict["ft_signal_index"],\
                                                    cmd_dict["ft_signal_no_index_list"])

        # Copy filename in the destination dir
        source = cmd_dict["module_filename"]
        dest = sf.output_dir + "/"  + os.path.basename(cmd_dict["module_filename"])
        shutil.copyfile(source, dest)

        #### Set instance connection basing on saved io_list_dict and param_list_dict
        in_connection_list = []
        out_connection_list = []
        param_connection_list = []
        # We cycle in all input 
        for sig_name in md_ft_module_obj.GetInputSigNamesList(): 
            # If the input is already connected in the instance
            if sig_name in cmd_dict["io_dict"].keys():
                # We verify that the connected signal exist in the main module and  we triplicate it
                # if is not alone
                for sig_to_connect in sf.md_main_block_obj.GetAllSigName():
                    if sig_to_connect in cmd_dict["io_dict"][sig_name]:
                        if sig_to_connect == cmd_dict["io_dict"][sig_name]:
                            in_connection_list.append(cmd_dict["io_dict"][sig_name])
                        else:
                            pre_suf_list = cmd_dict["io_dict"][sig_name].split(sig_to_connect)
                            new_conn = "{ " + pre_suf_list[0] + sig_to_connect + "[0]" + pre_suf_list[1] + ", "
                            new_conn += pre_suf_list[0] + sig_to_connect + "[1]" + pre_suf_list[1] + ", "
                            new_conn += pre_suf_list[0] + sig_to_connect + "[2]" + pre_suf_list[1] + "} "
                            in_connection_list.append(new_conn)
                        break

                else:
                    print("ERROR line %d, signal %s not found in main module !"%(sf.lineno, cmd_dict["io_dict"][sig_name]))
                    exit(-1)
            else:
                in_connection_list.append(sig_name)
        
        # We cycle in all input 
        for sig_name in md_ft_module_obj.GetOutputSigNamesList(): 
            # If the input is already connected in the instance
            if sig_name in cmd_dict["io_dict"].keys():
                # We verify that the connected signal exist in the main module and  we triplicate it
                # if is not alone
                for sig_to_connect in sf.md_main_block_obj.GetAllSigName():
                    if sig_to_connect in cmd_dict["io_dict"][sig_name]:
                        if sig_to_connect == cmd_dict["io_dict"][sig_name]:
                            out_connection_list.append(cmd_dict["io_dict"][sig_name])
                        else:
                            pre_suf_list = cmd_dict["io_dict"][sig_name].split(sig_to_connect)
                            new_conn = "{ " + pre_suf_list[0] + sig_to_connect + "[0]" + pre_suf_list[1] + ", "
                            new_conn += pre_suf_list[0] + sig_to_connect + "[1]" + pre_suf_list[1] + ", "
                            new_conn += pre_suf_list[0] + sig_to_connect + "[2]" + pre_suf_list[1] + "} "
                            out_connection_list.append(new_conn)
                        break

                else:
                    print("ERROR line %d, signal %s not found in main module !"%(sf.lineno, cmd_dict["io_dict"][sig_name]))
                    exit(-1)
            else:
                out_connection_list.append(sig_name)
        
        # We cycle in all input 
        for sig_name in md_ft_module_obj.GetParameterNamesList(): 
            # If the input is already connected in the instance
            if sig_name in cmd_dict["param_dict"].keys():
                # We verify that the connected signal exist in the main module and  we triplicate it
                # if is not alone
                param_connection_list.append(cmd_dict["param_dict"][sig_name])
            else:
                param_connection_list.append(sig_name)
        
        md_ft_module_obj.SetInputPortConnections(in_connection_list)
        md_ft_module_obj.SetOutputPortConnections(out_connection_list)
        md_ft_module_obj.SetParameterConnections(param_connection_list) 
        
        instance_name = md_ft_module_obj.GetModuleNameNoPrefix()


        #### Set new internal sig in the global variable
        sf.FindAndSetInternSigDictFromInstance(md_ft_module_obj)
        
        #### Create instance
        instance = md_ft_module_obj.GetInstance( instance_name, indent_int)
        

        return instance

    def GetSigFromStr(sf, string):
        stringa = string.split("[")[0]
        stringa = stringa.replace("{","")
        stringa = stringa.strip()
        return stringa

    def FindAndSetInternSigDictFromInstance(sf, md_module_obj):
        sig_name_bits = md_module_obj.GetAllConnectionSigNameAndBits()
        for sig_str, bits in zip(sig_name_bits[0], sig_name_bits[1]):
            sig = sf.GetSigFromStr(sig_str)
            # If the signal isn't in the IO we set it as internal
            if not sig in sf.md_main_block_obj.GetAllIoSigName():
                if not sig in sf.md_main_block_obj.GetInternSigNamesList():
                    if not sig in sf.new_internal_sig.keys():
                        sf.new_internal_sig[sig] = [bits, 0]
                    else:
                        sf.new_internal_sig[sig][1] += 1
                else:
                    if not sig in sf.new_internal_sig.keys():
                        sf.new_internal_sig[sig] = [bits, 0]



    def CreateAndSaveFtBlock(sf, md_obj, template_name, block_name, ft_sig_index, ft_sig_no_index_list):
        """ Return ft module object 
        This function use md_obj as "BLOCK" for ft template and create a ft block,
        the block is printed in the ft_filename file and than is Analyzed to create
        the ft object that is returned.
        ft_sig_index is used for parameter creation in sf.template_params_datafile
        """
        ft_filename = sf.output_dir+"/"+block_name+"_ft.sv" 

        ##### FT block creation
        # We use the template to transform the block in a ft block 
        
        param_name = md_obj.GetParamBaseNoPrefix() 
        #print(md_newmod_obj.GetInputSigNamesList()) 
        sf.tv_template_obj[template_name].SetModuleFilename("BLOCK", md_obj)
        # ft block creation from template
        ft_datafile = sf.tv_template_obj[template_name].\
                GetElaboratedTemplate(block_name, param_name)
        
        # ft parameter creation parameters template
        is_datafile = sf.tv_template_obj[template_name].\
                GetElaboratedTemplateParams(block_name, param_name)

        if is_datafile != 1:
            sf.template_params_datafile += is_datafile
            sf.template_params_datafile += sf.indent + "parameter int " + ft_sig_index\
                                                    +" = "+str(sf.block_cnt)+";\n"
            sf.block_cnt +=1
            sf.template_params_datafile += "\n\n"
        
        # Print ft_datafile
        fp = open(ft_filename,"w")
        fp.write(ft_datafile)
        fp.close()

        
        ##### Creation of FT module from previous written file
        # Get module info in order to create new instance of the ft block
        md_ft_module_obj = moddata(ft_filename, sf.module_prefix, sf.indent)
        # We give nd_newmod_obj at Analyze in order to create diff signals, we should create
        # this signal in order to connect it to signals vector and so use gived index
        md_ft_module_obj.Analyze(md_obj)
        #print(json.dumps(ft_module_info,indent=4))
        
        #### SET DIFF signals connnections
        if ft_sig_index != "":
            input_ft_sig_name_list = []
            output_ft_sig_name_list = []
            # Add to all ft signals the index, ft signals are diff signals find from Analyze function
            for ft_sig in md_ft_module_obj.GetInputSigDiffNamesList():
                if ft_sig in ft_sig_no_index_list:
                    input_ft_sig_name_list.append( ft_sig )
                else:
                    input_ft_sig_name_list.append( ft_sig+"["+ft_sig_index+"]" )

            for ft_sig in md_ft_module_obj.GetOutputSigDiffNamesList():
                if ft_sig in ft_sig_no_index_list:
                    output_ft_sig_name_list.append( ft_sig )
                else:
                    output_ft_sig_name_list.append( ft_sig+"["+ft_sig_index+"]" )
            
            # Set the input and output diff connection ports
            md_ft_module_obj.SetInputDiffPortConnections(input_ft_sig_name_list)
            md_ft_module_obj.SetOutputDiffPortConnections(output_ft_sig_name_list)

        return md_ft_module_obj


    def GetFtSignalIndex(sf, block_name):
        sf.orig_param_name = sf.md_main_block_obj.GetParamBaseNoPrefix()
        return  sf.orig_param_name + "_" + GetParamBase(block_name.replace(sf.module_prefix,"")) + "_I"

    def ElaborateHiddenTravulog(sf):
        """
         This function elaborate travulog code hidden in a verilog or sistemverilog file
         hidden travulog for command CREATE_FT_BLOCK appears like:
         //// CREATE_FT_BLOCK template_name block_name
         //// IN all input
         //// OUT all output
         //// END_CREATE_FT_BLOCK
        
         This type of code is useful when designer have a verilog hardware description that
         should became fault tolerant. In this case Hidden Travulog don't modify verilog
         code but can be analyzed by this function to create a new FT block for example.
         In this way any time that you apply a change in the original verilog, you could
         simulate you verilog and verify the behavior whitout delete Travulog code, then
         running this function your FT structure is created.
        """
        fp = open(sf.htravulog_filename,"r")
        data_orig=fp.read()
        data_orig=data_orig.replace("\t",sf.indent)

        data_line = data_orig.split("\n")

        data_elab=""
        sf.lineno=0
        linemax=len(data_line)
        cmd_dict={}
        create_ft_block_instance={}
        create_ft_block_datafile={}
        declaration_begin_line=0
        declaration_end_line=0
        # This list contain begin line, end line and name of a new block
        lines=[]
        ft_no_index_list = ["clk","rst_n"] 
        sf.block_cnt = 0
        sf.new_internal_sig = {}
        
        sf.package_datafile = ""

        # Elaboration cycle
        while sf.lineno < linemax:
            line= CompressLineSpaceTabs(data_line[sf.lineno])
            if line.split(" ")[0] == "module":
                declaration_begin_line = sf.lineno
            if line.split(" ")[0] == "logic":
                declaration_end_line = sf.lineno
            current_line_indent = GetStringIndent(data_line[sf.lineno], 8)

            # La stringa ////  l'indice di una riga di Travulog
            if line.split(" ")[0] == sf.HTKEY:

                cmd=line.replace(sf.HTKEY,"").strip()
                print("[Command] : " +cmd)

                if "CREATE_FT_BLOCK " in cmd:
                    cmd=" ".join(cmd.split())
                    cmd_list = cmd.split(" ")
                    ###########################
                    # Controls
                    ###########################
                    # The first line should contain three word
                    if len(cmd_list)!= 3 :  # CREATE_FT_BLOCK template_name block_name
                        print("ERROR line %d, CREATE_FT_BLOCK template_name block_name" % sf.lineno)
                        exit(-1)
                    if not cmd_list[1] in sf.tv_template_obj.keys():  # Errore se il template non e presente
                        print("ERROR line %d template %s not found"%sf.lineno,cmd_list[1])
                        exit(-1)
                    ##########################
                    # Parsing
                    ##########################
                    block_name = cmd_list[2]
                    cmd_dict[block_name]={}
                    cmd_dict[block_name]["template"] = cmd_list[1]
                    cmd_dict[block_name]["start_line"]=sf.lineno
                    # le linee di hidden travulog devono essere attaccate percui cerco
                    # sf.HTKEY nelle linee successive, devono infatti esserci gli ingressi e le uscite
                    sf.lineno += 1
                    line= " ".join(data_line[sf.lineno].strip().split()).strip()
                    # If this two variable are already false after cycle means that
                    # in out or both are not found in hidden travulog, this create an error
                    find_in=False
                    find_out=False
                    current_saving=""
                    # Save travulog hidden command
                    while line.split(" ")[0] == sf.HTKEY:
                        if " IN " in line:
                            current_saving="IN"
                            find_in=True
                            cmd_dict[block_name]["IN"]=[]
                        elif " OUT " in line:
                            current_saving="OUT"
                            find_out=True
                            cmd_dict[block_name]["OUT"]=[]
                        else:
                            if current_saving=="":
                                break
                        cmd_split = line.replace(sf.HTKEY, "").strip().split(" ")
                        if len(cmd_split) < 1:
                            break
                        if current_saving == "IN":
                            for ingressi in cmd_split:
                                if ingressi != "IN":
                                   cmd_dict[block_name]["IN"].append(ingressi)
                        if current_saving == "OUT":
                            for ingressi in cmd_split:
                                if ingressi != "OUT":
                                    cmd_dict[block_name]["OUT"].append(ingressi)

                        sf.lineno +=1
                        line= " ".join(data_line[sf.lineno].strip().split()).strip()

                    # Verify that both input and output are given
                    if not find_in or not find_out or \
                            len(cmd_dict[block_name]["IN"])<1 or \
                            len(cmd_dict[block_name]["OUT"])<1:

                        print("ERROR, line %d, hiddent travulog needs continuos statments"
                                ", CREATE_FT_BLOCK needs input and output signal, "
                                "you remember that IN and OUT need a space before and after"
                                " to be recognized" % sf.lineno)
                        exit(-1)

                    # Save verilog block to use in new block
                    cmd_dict[block_name]["verilog_block"] = data_line[sf.lineno]
                    sf.lineno +=1
                    line= " ".join(data_line[sf.lineno].strip().split()).strip()
                    while line.split(" ")[0] != sf.HTKEY:
                        cmd_dict[block_name]["verilog_block"] += data_line[sf.lineno] + "\n"
                        sf.lineno +=1
                        line= " ".join(data_line[sf.lineno].strip().split()).strip()

                    # Verify end key
                    if line.split(" ")[1] != "END_CREATE_FT_BLOCK":
                        print("ERROR, line %d, at the end of the verilog block"
                                " you should place END_CREATE_FT_BLOCK command" % sf.lineno)
                        exit(-1)

                    # Create datafile and instance
                    cmd_dict[block_name]["end_line"]=sf.lineno
                    lines.append([cmd_dict[block_name]["start_line"], sf.lineno, block_name])
                    cmd_dict[block_name]["block_name"] = block_name
                    # Index of the fault tolerant signals exiting from each ft block
                    cmd_dict[block_name]["ft_signal_index"] = sf.GetFtSignalIndex(block_name)
                    cmd_dict[block_name]["ft_signal_no_index_list"] = ft_no_index_list
                    
                    ft_instance= sf.CreateFtBlock( cmd_dict[block_name], current_line_indent)

                    cmd_dict[block_name]["instance"] = ft_instance

                elif "INSTANCE_AND_BLOCK_TO_FT " in cmd:
                    """
                    This command can be applied only to an instance of a block, 
                    the program save:
                        module name of the instance
                        instance name
                        list of parameter, list of paramter connected
                        list of input signal, list of signal connected to input
                        list of output signal, list of signal connected to output
                     After the command string " INSTANCE_AND_BLOCK_TO_FT " the program needs
                     the template name and the filename of the module instanced, the path
                     of the filename should be relative to the main module directory, so the 
                     general syntax is:
                            INSTANCE_AND_BLOCK_TO_FT template_name instanced_module_filename
                     Inside the htravulog commands "//// INSTANCE_AND_BLOCK_TO_FT" and 
                     "//// END_INSTANCE_AND_BLOCK_TO_FT" there should be the instance of the block
                     indicated as the second argument. This instance will be used to connect correctly
                     the signals to the new instance of the ft block.
                    """
                    cmd=" ".join(cmd.split())
                    cmd_list = cmd.split(" ")
                    ###########################
                    # Controls
                    ###########################
                    # The first line should contain three word
                    if len(cmd_list)!= 3 :  # INSTANCE_AND_BLOCK_TO_FT template_name instanced_module_filename
                        print("ERROR line %d, INSTANCE_AND_BLOCK_TO_FT template_name instanced_module_filename" \
                                    % sf.lineno)
                        exit(-1)
                    if not cmd_list[1] in sf.tv_template_obj.keys():  # Errore se il template non e presente
                        print("ERROR line %d template %s not found"%sf.lineno,cmd_list[1])
                        exit(-1)
                    ##########################
                    # Parsing
                    ##########################
                    template_name = cmd_list[1]
                    module_filename = sf.input_dir + "/"+ cmd_list[2]
                    mod_fname_path = Path(module_filename)
                    if not mod_fname_path.is_file() :
                        print("ERROR line %d, filename don't exist, use absolute path or relative to current dir"%sf.lineno)
                        exit(-1)

                    oldline = line
                    start_line = sf.lineno
                    search_blockname = True
                    save_parameter = False
                    save_io = False
                    end_save = False

                    sf.lineno += 1
                    while not "END_INSTANCE_AND_BLOCK_TO_FT" in data_line[sf.lineno] and sf.lineno < linemax:
                        line= CompressLineSpaceTabs(data_line[sf.lineno])
                        if not end_save:
                            # We find the blockname with parameter
                            if "#(" in line and search_blockname:
                                current_line_indent = GetStringIndent(data_line[sf.lineno], 8)
                                if len(line.split(" ")) > 1:
                                    if line.split(" ")[0] != "#(":
                                        block_name = line.split(" ")
                                        search_blockname = False
                                        save_parameter = True
                                    else:
                                        print("ERROR in parsing, line %d"% sf.lineno)
                                        exit(-1)
                                else:
                                    block_name = oldline.split(" ")[0]
                                    cmd_dict[block_name]={}
                                    cmd_dict[block_name]["block_name"] = block_name
                                    cmd_dict[block_name]["template"] = template_name
                                    cmd_dict[block_name]["start_line"] = start_line
                                    cmd_dict[block_name]["module_filename"] = module_filename
                                    cmd_dict[block_name]["param_dict"] = {}
                                    cmd_dict[block_name]["io_dict"] = {}
                                    cmd_dict[block_name]["ft_signal_index"] = sf.GetFtSignalIndex(block_name)
                                    cmd_dict[block_name]["ft_signal_no_index_list"] = ft_no_index_list
                                    
                                    search_blockname = False
                                    save_parameter = True
                            
                            # We find the blockname witout
                            elif "(" in line and search_blockname:
                                if len(line) == 1:
                                    if len(oldline.split(" ")) == 2:
                                        block_name = oldline.split(" ")[0]
                                        cmd_dict[block_name]={}
                                        cmd_dict[block_name]["instance_name"] = oldline.split(" ")[1]
                                    else:
                                        print("ERROR while parsing line %d" % sf.lineno)
                                        exit(-1)
                                else:
                                    if len(line.split(" ")) < 2:
                                        print("ERROR line %d while parsing" % sf.lineno)
                                        exit(-1)
                                    block_name = line.split(" ")[0]
                                    cmd_dict[block_name]={}
                                    cmd_dict[block_name]["instance_name"] = line.split(" ")[1].replace("(","")
                                        
                                search_blockname = False
                                save_io = True
                                    
                                cmd_dict[block_name]["block_name"] = block_name
                                cmd_dict[block_name]["template"] = template_name
                                cmd_dict[block_name]["start_line"] = start_line
                                cmd_dict[block_name]["module_filename"] = module_filename
                                cmd_dict[block_name]["param_dict"] = {}
                                cmd_dict[block_name]["io_dict"] = {}
                                cmd_dict[block_name]["ft_signal_index"] = sf.GetFtSignalIndex(block_name)
                                cmd_dict[block_name]["ft_signal_no_index_list"] = ft_no_index_list
                                    
                            # We save parameter connections
                            elif "." in line and save_parameter:
                                if re.findall("\)\W*,",line)!= [] or re.findall(r'\)\W*\)*', line)!=[]:
                                    if len(re.findall(r'\)\W*\)', line)) != 0:
                                        save_parameter = False
                                        save_io = True
                                    # We eliminate ( , ) and . from the line in order to have 
                                    # only the name of the port and of the signal to connect
                                    line_param_list = SplitInstanceLine(line)
                                    if len(line_param_list) != 2:
                                        print("ERROR in parser line %d, multiple instance on the same line not "
                                            "implemented in  the parser 1" % sf.lineno)
                                        exit(-1)
                                    
                                    # We create a list of dict where the key is the name of the parameter
                                    # of module and the value is the connection do to, the dictionary is created because
                                    # the order of connection can be different, we then reordered the list of connection
                                    cmd_dict[block_name]["param_dict"][line_param_list[0]] = line_param_list[1]
                                        
                                else:
                                    print("ERROR line %d, multiple instance on the same line not implemented in"
                                            " the parser 2" % sf.lineno)
                                    exit(-1)
                            
                            # We save io connections
                            elif "." in line and save_io:
                                if re.findall("\)\W*,",line)!= [] or re.findall(r'\)\W*\)*', line)!=[]:
                                    # If we are in the last line of the declaration
                                    if len(re.findall(r'\)\W*\)\W*;', line)) != 0:
                                        end_save = True
                                    # split line
                                    line_param_list = SplitInstanceLine(line)
                                    # Verify that there is only  one declaration for line
                                    if len(line_param_list) != 2:
                                        print("ERROR in parser line %d, multiple instance on the same line not "
                                            "implemented in  the parser 3" % sf.lineno)
                                        exit(-1)
                                    cmd_dict[block_name]["io_dict"][line_param_list[0]] = line_param_list[1]

                                else:
                                    print("ERROR line %d, multiple instance on the same line not implemented in"
                                            " the parser 4 " % sf.lineno)
                                    exit(-1)

                            elif ")" in line and not ";" in line:
                                if len(SplitInstanceLine(line)) == 1: 
                                    if len(line) == 1:
                                        sf.lineno +=1 
                                        line = CompressLineSpaceTabs(data_line[sf.lineno])
                                        cmd_dict[block_name]["instance_name"] = line.split(" ")[0].replace("(","")
                                    else:
                                        cmd_dict[block_name]["instance_name"] = line.replace(")","").replace("(","")
                                else:
                                    if line.split(" ")[0] == ")":
                                        cmd_dict[block_name]["instance_name"] = line.split(" ")[1].replace("(","")
                                    else:
                                        cmd_dict[block_name]["instance_name"] = line.split(" ")[0].replace(")","").replace("(","")
                                
                                save_parameter = False
                                save_io = True
                            
                            elif "(" in line and len(CompressLineSpaceTabs(line)) == 1:
                                save_parameter = False
                                save_io = True

                            elif re.findall(r'\)\W*;', line) != []:
                                end_save = True

                            #else:
                                #print("ERROR in parsing line %d, something goes wrong" % sf.lineno)
                                #exit(-1)

                        oldline = line
                        sf.lineno +=1

                    # END PARSING WHILE
                        
                    cmd_dict[block_name]["end_line"]=sf.lineno
                    lines.append([cmd_dict[block_name]["start_line"], sf.lineno, block_name])
                        
                    #print(json.dumps(cmd_dict[block_name],indent=4))
                    cmd_dict[block_name]["instance"] = sf.BlockToFT(cmd_dict[block_name], current_line_indent)
                    #print(cmd_dict[block_name]["instance"]) 

                    # le linee di hidden travulog devono essere attaccate percui cerco
                    # sf.HTKEY nelle linee successive, devono infatti esserci gli ingressi e le uscite
                    sf.lineno += 1
                    line= " ".join(data_line[sf.lineno].strip().split()).strip()

            # END IF HTKEY in line

            sf.lineno+=1

        # END CYCLE on file lines

        ########################################################################
        # Create the new file of original block module_info
        ########################################################################
        # print(json.dumps(cmd_dict,indent=4))

        sf.lineno = 0
        datafile = ""

        # Copy the beginning of the file before IO declaration
        while sf.lineno < declaration_begin_line:
            datafile += data_line[sf.lineno] + "\n"
            sf.lineno +=1

        sf.md_main_block_obj.DeleteInternSigs()
        for sig, bits_num in zip(sf.new_internal_sig.keys(), sf.new_internal_sig.values()):
            bits = bits_num[0]
            num = bits_num[1]
            if num != 0:
                bits["N1UP"] = num
                bits["N1DW"] = 0
            sf.md_main_block_obj.AppendInternSig(sig, bits)

        sf.new_internal_sig
        # Add declaration and internal signals
        
        datafile += "module " + sf.md_main_block_obj.GetModuleName()+ "_ft" + "\n"
        datafile += sf.md_main_block_obj.GetDeclaration(0, {"N1UP":2 , "N1DW":0}, ft_no_index_list)

        sf.lineno = declaration_end_line + 1
        # Add all internal verilog and the instance of the new block if they exist
        i=0
        while sf.lineno < len(data_line):
            if len(lines) > 0:
                if i < len(lines) and sf.lineno == lines[i][0]:
                    datafile += cmd_dict[lines[i][2]]["instance"]
                    # Jump to the end of the new block declaration
                    sf.lineno = lines[i][1]+1
                    print("Created instance %s" % lines[i][2])
                    i+=1

            datafile += data_line[sf.lineno] + "\n"
            sf.lineno+=1
        
        converted_htravulog = sf.output_dir + "/" + sf.htravulog_filename.replace(".sv","_ft.sv").split("/")[-1]
        fp = open( converted_htravulog, "w")
        fp.write(datafile)

        fp = open(sf.package_filename, "r")
        data = fp.read()
        new_data = data.replace("TEMPLATE_PARAMETERS_DEFINITION", sf.template_params_datafile)
        new_package_filename = sf.output_dir + "/" + sf.package_filename.replace(".sv","_ft.sv").split("/")[-1]
        fp = open(new_package_filename, "w")
        fp.write(new_data)

        return datafile


            
