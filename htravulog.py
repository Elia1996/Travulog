#!/usr/bin/python3
import sys
import os
import re
import json
from pathlib import Path
import shutil
import os.path
import inspect


from moddata import *
from travulog import *

def linenum():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno

def CompressInstanceLine(line):
    """ return an instance line compressed
    e.g: ".PULP_OBI          ( PULP_OBI                    )," became "PULP_OBI#PULP_OBI"
    ".branch_addr_i     ( {branch_addr_n[31:1], 1'b0} )," became "branch_addr_i#{branch_addr_n[31:1], 1'b0}"
    """
    line_no_space = CompressLineSpaceTabs(line)
    line1 = line_no_space.replace(".", " ").replace("(","#")
    line2 = re.sub(r'\)\W*,' , ' ' , line1)
    line2 = re.sub(r'\)\W*\)*' , ' ' , line2)
    line3 = RemoveComments(line2)
    line3 = line3.replace(" # ", "#")
    line_compress = CompressLineSpaceTabs(line3)
    return line_compress

def SplitInstanceLine(line):
    """ return an instance line splitted in [ signal to connect, connection]
    e.g: ".PULP_OBI          ( PULP_OBI                    )," became ["PULP_OBI","PULP_OBI"]
    ".branch_addr_i     ( {branch_addr_n[31:1], 1'b0} )," became ["branch_addr_i" , "branch_addr_n[31:1], 1'b0}"]
    """
    return CompressInstanceLine(line).split("#")

def VerifyFile(filename, error=""):
    """ This function verify that a string correspond to a real filename
    otherwise print an error.
    """
    if not os.path.isfile(filename):
        print("[%d] ERROR1 %s, file %s don't exist"%(linenum(), error, filename))
        exit(-1)

def VerifyDir(directory, error=""):
    """ This function verify that a string correspond to a real directory
    otherwise print an error.
    """
    if not os.path.isdir(directory):
        print("[%d] ERROR2 %s, directory %s don't exist"%(linenum(), error, directory))
        exit(-1)

def IsStartKey(line ,keyword):
    if re.match("^\W*"+keyword+"\W.*$", line)!=None or re.match("^"+keyword+"\W*$", line) != None  :
        return True
    return False

def IsEndKey(line, keyword):
    if "END_"+keyword in line  :
        return True
    return False

def SetInstanceConnection(block_obj,  command, lineno, upper_block_obj = None, old_connection_dict=None , HTKEY = "////", debug = False):
    """
    """
   
    """ Creation of the dictionary with the commands, cmd_dict is a dictionary like:
        {"IN":[ { "siglist":[ "clk", "rst_n"], "pattern": "PRECONSIG_trSUFCON" },{"siglist":[], "pattern": "PRECONSIGSUFCON" }],
        {"OUT": [ {"siglist":[], "pattern": "PRECONSIGSUFCON"}] }
    """
    cmd_dict = GetCmdElab(block_obj, command, lineno,  HTKEY)

    # This dictionary connect each port with the corresponding signal, this is
    # the dictionary that will be created in this function and will be used to set connection inside the object
    port_connection_dict = {}


    block_obj_sigs = {"IN":block_obj.GetInputSigNamesList()+block_obj.GetInputSigDiffNamesList(),
                    "OUT":block_obj.GetOutputSigNamesList()+block_obj.GetOutputSigDiffNamesList()}
    if upper_block_obj != None:
        upper_block_obj


    conn_sig = ""
    conn_precon = ""
    conn_sufcon = ""
    if debug:
        print("OldConnection")
        print(old_connection_dict)

    # We cycle on each io of the module
    for io_id in ["IN","OUT"]:
        # For each IO_ID we cycle through the list of corresponding command saved in  cmd_dict
        for single_cmd_dict in cmd_dict[io_id]:
            if debug:
                print("Siglist")
                print(json.dumps(single_cmd_dict["siglist"],indent=4))
            pattern  = single_cmd_dict["pattern"]
            conn_precon = ""
            conn_sufcon = ""
            # If the siglist is != [] means that there is a condition like a if and so there is a 
            # list of signal on which apply a certain pattern, instead if the siglist is == []
            # we should cycle on the remaning signals and connect it with the corresponding pattern
            if single_cmd_dict["siglist"] == []:
                for mod_io_sig_name in block_obj_sigs[io_id]:
                    if not mod_io_sig_name in port_connection_dict.keys():
                        if old_connection_dict != None: 
                            if mod_io_sig_name in old_connection_dict.keys():
                                for sig_conn in upper_block_obj.GetAllSigName():
                                    if SigMatch(sig_conn,old_connection_dict[mod_io_sig_name]):
                                        sig_split = old_connection_dict[mod_io_sig_name].split(sig_conn) # [ '{' , '[31:1], 1'b0}' ]
                                        conn_sig = sig_conn
                                        break
                                else:
                                    print("Connection not found 1")
                                    exit(1)
                            else:
                                conn_sig = mod_io_sig_name
                                sig_split = ["",""]    
                            conn_precon = sig_split[0]
                            conn_sufcon = sig_split[1]
                        else:
                            conn_sig = mod_io_sig_name 
                        newsig = pattern.replace("SIG", conn_sig ).replace("PRECON", conn_precon).replace("SUFCON",conn_sufcon)
                        if debug:
                            print("connection1 : %s %s , newsig: %s"%(mod_io_sig_name, conn_sig, newsig))
                        port_connection_dict[mod_io_sig_name] = newsig
                break
            
            else:
                for sig_to_find in single_cmd_dict["siglist"]:
                    if not sig_to_find in port_connection_dict.keys():
                        if debug:
                            print("signal: %s"%sig_to_find)
                        for mod_io_sig_name in block_obj_sigs[io_id]:
                            # In this case the signal indicated in the list is an IO of the module
                            if sig_to_find == mod_io_sig_name:
                                if old_connection_dict != None:
                                    if mod_io_sig_name in old_connection_dict.keys():
                                        for sig_conn in upper_block_obj.GetAllSigName():
                                            if SigMatch(sig_conn, old_connection_dict[sig_to_find]):
                                                sig_split = old_connection_dict[sig_to_find].split(sig_conn) # [ '{' , '[31:1], 1'b0}' ]
                                                conn_sig = sig_conn
                                                break
                                        else:
                                            print("Connection not found 2")
                                            exit(1)
                                    else:
                                        conn_sig = mod_io_sig_name
                                        sig_split = ["",""]    

                                    conn_precon = sig_split[0]
                                    conn_sufcon = sig_split[1]
                                else:
                                    conn_sig = sig_to_find 
                                    conn_precon = ""
                                    conn_sufcon = ""
                                newsig = pattern.replace("SIG", conn_sig ).replace("PRECON", conn_precon).replace("SUFCON",conn_sufcon)
                                if debug:
                                    print("connection2 : %s %s , newsig: %s"%(sig_to_find, conn_sig , newsig))
                                port_connection_dict[sig_to_find] = newsig
                                break
                        else:
                            # In this case the signal to find in the list is a signal owned by the upper module
                            if old_connection_dict != None:
                                for sig, sig_con in zip(old_connection_dict.keys(), old_connection_dict.values()):
                                    if SigMatch(sig_to_find,sig_con):
                                        sig_split = old_connection_dict[sig].split(sig_to_find) # [ '{' , '[31:1], 1'b0}' ]
                                        conn_sig = sig_to_find 
                                        conn_precon = sig_split[0]
                                        conn_sufcon = sig_split[1]
                                        newsig = pattern.replace("SIG", conn_sig ).replace("PRECON", conn_precon).replace("SUFCON",conn_sufcon)
                                        if debug:
                                            print("connection3 : %s %s , newsig: %s"%(sig_to_find, conn_sig , newsig))
                                        port_connection_dict[sig] = newsig
                                        break
                                else:
                                    print("Warning: line %d, signal %s not found in the connection of instance"%(lineno, sig_to_find))
                            else:
                                print("Warning: line %d, signal %s not found in the connection IO of instance"%(lineno, sig_to_find))
        
    port_connection_list= {"IN":[], "OUT":[], "INDIFF":[], "OUTDIFF":[]}
    if debug:
        print(port_connection_dict)
    for sig_tc_name, sig_tc_type in zip(block_obj.GetAllIoSigName()+block_obj.GetAllDiffSigName(), 
                                        block_obj.GetAllIoSigType()+block_obj.GetAllDiffSigType()):
        if not sig_tc_name in port_connection_dict.keys():
            port_connection_list[sig_tc_type].append(sig_tc_name)
        else:
            port_connection_list[sig_tc_type].append(port_connection_dict[sig_tc_name])
    
    if debug:
        print(port_connection_list)

    block_obj.SetInputPortConnections(port_connection_list["IN"])
    block_obj.SetOutputPortConnections(port_connection_list["OUT"])
    block_obj.SetInputDiffPortConnections(port_connection_list["INDIFF"])
    block_obj.SetOutputDiffPortConnections(port_connection_list["OUTDIFF"])

    return block_obj

def SigMatch(sig,text):
    m1 =  re.match(r"^"+sig+"$",text)
    m2 =  re.match(r"^"+sig+"\W+.*$",text)
    m3 = re.match(r"^.*\W+"+sig+"$",text)
    m4 = re.match(r"^.*\W+"+sig+"\W.*$",text)
    m5 = re.match(r"^.* "+sig+" .*$",text)
    if m1 or m2 or m3 or m4 or m5:
        return True
    return False




class htravulog:
    def __init__(sf, htravulog_filename, indent = "        "):
        """
        htravulog_filename -> filename of the verilog file with htravulog code
        """
        VerifyFile(htravulog_filename)
        sf.htravulog_filename = htravulog_filename
        sf.dprint_fname = sf.htravulog_filename
        sf.htravulog_dirname = os.path.dirname(htravulog_filename)
        sf.indent = indent
        sf.indent_int = len(indent)
        sf.HTKEY="//// "
        sf.HTPATTERN= "^\W*//// "

        # Creation of moddata object
        sf.md_main_mod_obj = moddata(sf.htravulog_filename, indent)
        sf.md_main_mod_obj.Analyze()
        [sf.IN_ID, sf.OUT_ID, sf.INTERN_ID, 
                sf.INDIFF_ID, sf.OUTDIFF_ID, sf.PARAM_ID] = sf.md_main_mod_obj.GetAllIds()

        # Error base string
        sf.ErrorBaseStr = "ERROR3 in file "+sf.htravulog_filename+" "

        # Htravulog filename variables
        sf.main_mod_datafile = open(sf.htravulog_filename ,"r").read()
        sf.main_mod_datafile = sf.main_mod_datafile.replace("\t",indent)
        sf.main_mod_datafile_lines_list = sf.main_mod_datafile.split("\n")
        sf.lineno = 0

        # Package Variables from import
        sf.htpkg_filename = ""
        sf.input_dir = ""
        sf.output_dir = ""
        sf.module_prefix = ""
        sf.pkg_file = ""
        sf.pkg_out_file = ""
        sf.templates = {}
        
        # datafile used to append new parameters using the param template
        sf.parameters_datafile = ""

        # New module parameter
        sf.new_module_name = ""
        sf.md_main_new_mod_obj = sf.md_main_mod_obj
        sf.new_module_filename = ""
        sf.new_verilog_block_list = ""
        sf.new_intern_definitions = ""
        
        # New signals created by the add_module_layer
        # These are dictionary like { signame:sigbit , ...}
        sf.ADM_new_mod_input_sig = {}

        sf.ADM_new_mod_output_sig = {}

        # Signal used as last
        sf.last_module_name = ""
        sf.last_param_name = ""
        sf.last_tv_obj = None
        sf.last_current_mod_id = ""

        # Datafile in which are saved the parameter file trasformed, this datafile
        # will be placed in the pkg_file
        sf.templates_param_datafile = ""

        # Dictionary of commands and related functions
        sf.command_func_dict = {"ADD_MODULE_LAYER": sf.AddModuleLayer ,
                             "CREATE_MODULE" : sf.CreateModule}
        sf.command_intern_dict = {"FOREACH" : sf.Foreach}

        

        sf.debug = False


    ###########################################################################################################
    # Main Elaboration
    ###########################################################################################################
    def ElaborateHiddenTravulog(sf):
        """ Elaborate the htravulog file and return the new module 
        The file is divided in 4 parts, the section before the module declaration, the io section, the intern
        signal declaration section and the verilog block section. Each part is elaborated in the corresponding
        function
        """
        
        # Elaborate the section before the module definition setting all variable through 
        # IMPORT and NEW_MODULE_NAME keyword
        sf.ElaborateBeforeModule()

        sf.ElaborateVerilogBlock()

        sf.ElaborateIntern()
        
        # We save the parameters file   
        fp = open(sf.pkg_file, "r")
        pkg_datafile = fp.read()
        pkg_datafile = pkg_datafile.replace("TEMPLATE_PARAMETERS_DEFINITION", sf.parameters_datafile)
        pkg_datafile =  pkg_datafile.replace("MAIN_MOD_ID",sf.md_main_mod_obj.GetParamBaseNoPrefix())
        fp.close()
        fp = open(sf.pkg_out_file, "w")
        fp.write(pkg_datafile)
        fp.close()


        # We save the change done to the main module 
        datafile = sf.md_main_new_mod_obj.GetCompleteVerilog()
        fp = open(sf.new_module_filename, "w")
        fp.write(datafile)
        fp.close()




    ###########################################################################################################
    # Elaboration of Sections
    ###########################################################################################################
    
    def ElaborateBeforeModule(sf):
        """ Import htravulog package and set module_name
        The commands to use in this section are:
        
        //// IMPORT filename
        //// NEW_MODULE_NAME name_of_new_module
        """
        # Save before module block
        [ start_line, end_line ] = sf.md_main_mod_obj.GetBeforeModuleLines()
        sf.dprint("Line before module [%d,%d]"%(start_line, end_line))

        # Flag to verify that user set new module name
        flag_new_module_name = False
        flag_new_module_file = False
        
        # Current line visible everyware
        sf.lineno = start_line
        sf.dprint_fname = sf.htravulog_filename

        new_before_module = ""
        # Cycle on code before the module declaration
        for line in sf.main_mod_datafile.split("\n")[start_line: end_line]:
            if sf.IsHtravulogCode(line):
                code_list = sf.GetHtravulogCode(line).split(" ")
                if "IMPORT " in line:
                    sf.dprint(line)
                    sf.EBMSetImport(code_list)
                    sf.dprint_fname = sf.htravulog_filename
                elif "NEW_MODULE_NAME " in line:
                    sf.dprint(line)
                    sf.EBMSetNewModuleName(code_list)
                    flag_new_module_name = True
                elif "NEW_MODULE_FILE " in line:
                    sf.dprint(line)
                    sf.EBMSetNewModuleFilename(code_list)
                    flag_new_module_file = True
                elif "ADD_LINE " in line:
                    sf.dprint(line)
                    new_before_module += CompressLineSpaceTabs(line.replace("ADD_LINE","").replace(sf.HTKEY,""))
            else:
                new_before_module += line + "\n"

            sf.lineno += 1

        sf.md_main_mod_obj.SetBeforeModule(new_before_module)

        if not flag_new_module_name:
            sf.htvfileerror("you should set the name of new module to create with \"NEW_MODULE_NAME name\"")
        if not flag_new_module_file:
            sf.htvfileerror("you should set the name of new module file with \"NEW_MODULE_FILE name\"")


    def ElaborateIo(sf):
        """ Change the io of the module according to htravulog code
        The commands to use in this section are:
        
        //// FOREACH <MAIN_MODULE> <IN|OUT|INTERN|PARAM> [NOT sig1 sig2 ...]
        ////     SystemVerilog_line
        //// END_FOREACH

        """

    def ElaborateIntern(sf):
        """ Change the internal signals of the module according to htravulog code
        The commands to use in this section are:
        
        //// FOREACH <MAIN_MODULE> <IN|OUT|INTERN|PARAM> [NOT sig1 sig2 ...]
        ////     SystemVerilog_line
        //// END_FOREACH
        
        This section musts end with
        END_DECLARATIONS
        If there will be declaration after this command they aren't considered
        """
        [ start_line, end_line ] = sf.md_main_mod_obj.GetInternLines()

        sf.intern_sig_start_line = start_line
        intern_code = sf.main_mod_datafile_lines_list[start_line:end_line]

        cmd_lod = sf.EVBGetCodePattern( intern_code, list(sf.command_intern_dict.keys()))

        
        for cmd_dict in cmd_lod:
            if cmd_dict["nesting"] != 0:
                sf.HTVFileError("In function ElaborateIntern, you can use nested command in the intern definition")
            # Execute all htravulog command gived
            command_block_l =  intern_code[cmd_dict["start_line"] : cmd_dict["end_line"]+1]
            start_line_new_block = cmd_dict["start_line"]
            sf.command_intern_dict[cmd_dict["name"]](start_line_new_block, command_block_l, cmd_dict["indent_int"])


        sf.md_main_new_mod_obj.SetInternSigBlock(sf.new_intern_definitions )
        

    def ElaborateVerilogBlock(sf):
        """ Elaborate htravulog in the architecture definition block
        The commands to use in this section are:
        
        Creation of a new module using a verilog block in the current module,
        the htravulog code and the verilog code inside are replaced with
        the instance of the new module:
           //// CREATE_MODULE new_module_name
           //// OUTFILE filename_of_output_file
           ////
           //// IN sig1 sig2 ...
           //// sign END_IN
           //// OUT sig1 sig2 ...
           //// sign END_OUT
                verilog code
           //// END_CREATE_MODULE

        This command create a new SystemVerilog module from an existing module and 
        it substitute the current instance with a new one that connect the new module.
           ////  ADD_MODULE_LAYER
           ////  TEMPLATE template_id
           ////  INFILE filename_of_input
           ////  OUTFILE filename_of_output
           ////
           ////  CONNECT [IF MAIN_MOD_[IN|OUT|INTERN|PARAM]|NEW_[IN|OUT|INTERN|PARAM] ] IN = [prefix_]IN[_suffix]
           ////          [IF MAIN_MOD_[IN|OUT|INTERN|PARAM]|NEW_[IN|OUT|INTERN|PARAM] ] OUT = [prefix_]OUT[_suffix]
           ////  END_CONNECT
                     verilog code
           ////  END_ADD_MODULE_LAYER

        """
        # Save verilog block using main module object
        [ start_line, end_line ] = sf.md_main_mod_obj.GetVerilogBlockLines()
        sf.dprint("Line Verilog Block [%d,%d]"%(start_line, end_line))
        sf.vblock_start_line = start_line

        # Create a copy of the verilog block
        sf.new_verilog_block_list = sf.main_mod_datafile_lines_list[start_line:end_line]

        # Command list of dict like:
        # [{"nesting":0, "name":"CREATE_MODULE", "start_line":10, "end_line":30, "indent_int": 1}, ...]
        # The list is ordered by nesting key, first element have higher nesting. In this 
        # way we can execute firt nested command and then others.
        cmd_lod = sf.EVBGetCodePattern(sf.new_verilog_block_list,  list(sf.command_func_dict.keys()))

        module_index = 0
        # Execute all htravulog command gived
        while cmd_lod != []:
            cmd_dict = cmd_lod[0]
            command_block_l =  sf.new_verilog_block_list[cmd_dict["start_line"] : cmd_dict["end_line"]+1]
            start_line_new_block = cmd_dict["start_line"]
            sf.new_verilog_block_list = sf.command_func_dict[cmd_dict["name"]](start_line_new_block, command_block_l, cmd_dict["indent_int"])
            # If the nesting is 0 we transform the parameters and save it in a datafile, it will then write into the sf.pkg_file
            if cmd_dict["nesting"] == 0:
                sf.last_module_name 
                sf.last_param_name 
                datafile = sf.last_tv_obj.GetElaboratedTemplateParams(sf.last_module_name, sf.last_param_name)
                if datafile != 1:
                    datafile = datafile.replace("CURRENT_MOD_ID", sf.last_current_mod_id)
                    sf.parameters_datafile += datafile.replace("MODULE_ORDER", str(module_index))
                    sf.parameters_datafile += "\n\n"
                module_index += 1
            
            cmd_lod = sf.EVBGetCodePattern(sf.new_verilog_block_list,  list(sf.command_func_dict.keys())) 

        sf.md_main_new_mod_obj.SetVerilogBlock("\n".join(sf.new_verilog_block_list) )
    
    ###########################################################################################################
    # Htravulog command functions used in ElaborateIntern
    ###########################################################################################################

    def Foreach(sf, start_line_new_code, command_block_l, indent_int):
        """This function elaborate a code block with this syntax:
        //// FOREACH <MAIN_MODULE> <IN|OUT|INTERN|PARAM> [NOT sig1 sig2 ...]
        ////     SystemVerilog_line
        //// END_FOREACH    
        The new signals are added to the block intern_sig text that is used when 
        you call obj.GetCompleteVerilog()
        """
        ################################################################################
        #### 1) Parse the htravulog code
        
        param_dict = { "MAIN_MOD_IN": sf.md_main_mod_obj.GetInputSigNamesList(),
                       "MAIN_MOD_OUT": sf.md_main_mod_obj.GetOutputSigNamesList(),
                       "MAIN_MOD_INTERN": sf.md_main_mod_obj.GetInternSigNamesList(),
                       "MAIN_MOD_PARAM": sf.md_main_mod_obj.GetParameterNamesList(),
                       "MAIN_MOD_ID": sf.md_main_mod_obj.GetParamBaseNoPrefix(),
                       "NEW_IN": list(sf.ADM_new_mod_input_sig.keys()),
                       "NEW_OUT": list(sf.ADM_new_mod_output_sig.keys())
                       }

        real_line = sf.intern_sig_start_line + start_line_new_code
        
        # code_list should be : 
        #   {"code_list" : ["MAIN_MOD OUT", "logic [2:0]BITINIT SIGNAME_tr;"],
        #   "verilog_block": ""}
        raw_code_dict = sf.GetInnerCmdDict(0, command_block_l, "FOREACH", htravulog = True)
        raw_code_list = raw_code_dict["code_list"]
        
        sig_text = raw_code_list[0]
            
        for param, sig_list in zip(param_dict.keys(), param_dict.values()):
            if type(sig_list) == list:
                sig_text = re.sub(param+" ", " ".join(sig_list), sig_text)
                sig_text = re.sub("^"+param+"$", " ".join(sig_list), sig_text)
            else:
                sig_text = re.sub(param+" ", sig_list, sig_text)
                sig_text = re.sub("^"+param+"$", sig_list, sig_text)

        if "NOT" in sig_text:
            sig_text_l = sig_text.split("NOT")
            sig_l =CompressLineSpaceTabs( sig_text_l[0]).split(" ")
            not_sig_l = CompressLineSpaceTabs( sig_text_l[1]).split(" ")
            sig_text = ""
            for sig in sig_l:
                if not sig in not_sig_l:
                    sig_text+=sig +" "

            sig_text =  sig_text.strip()
            sf.dprint("NOTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT")
            sf.dprint(sig_text)



        sig_text = CompressLineSpaceTabs(sig_text)
        model_text = "\n".join(raw_code_list[1:])

        sf.dprint(sig_text)
        sf.dprint(model_text)
        
        ################################################################################
        #### 2) Create the definition saving in sf.new_intern_definitions

        for sig in sig_text.split(" "):
            sf.dprint("-----%s"%model_text)
            new_line =  model_text.replace("SIGNAME", sig)
            [there_is, lista] = sf.md_main_mod_obj.GetSigData(sig)
            if not there_is :
                if sig in sf.ADM_new_mod_input_sig.keys():
                    sig_bit = sf.ADM_new_mod_input_sig[sig]
                    sig_type = sf.md_main_mod_obj.IN_ID
                elif sig in sf.ADM_new_mod_output_sig.keys():
                    sig_bit = sf.ADM_new_mod_output_sig[sig]
                    sig_type = sf.md_main_mod_obj.OUT_ID
                else:
                    sf.HTVFileError("In Foreach")
            else:
                [sig_type,  sig_name, sig_bit] = lista

            bitdef = CreateBitsDefinition(sig_bit)
            new_line = new_line.replace("INOUT",sig_type).replace("BITINIT",bitdef) 

            for line in new_line.split("\n"):
                sf.new_intern_definitions += (indent_int)*sf.indent+line+"\n" 

        sf.new_intern_definitions += "\n"
        sf.dprint(sf.new_intern_definitions)
        return sf.new_intern_definitions
            

    ###########################################################################################################
    # Htravulog command functions used in ElaborateVerilogBlock and declared in sf.command_func_dict
    ###########################################################################################################
    
    def AddModuleLayer(sf, start_line_new_code, command_block_l, indent_int):
        """ This function elaborate a code block with this syntax:
           ////  ADD_MODULE_LAYER
           ////  TEMPLATE template_id
           ////  INFILE filename_of_input
           ////  OUTFILE filename_of_output
           ////
           ////  CONNECT [IF MAIN_MOD_[IN|OUT|INTERN|PARAM]|NEW_[IN|OUT|INTERN|PARAM] ] IN = [prefix_]IN[_suffix]
           ////          [IF MAIN_MOD_[IN|OUT|INTERN|PARAM]|NEW_[IN|OUT|INTERN|PARAM] ] OUT = [prefix_]OUT[_suffix]
           ////  END_CONNECT
                 verilog instance
           ////  END_ADD_MODULE_LAYER
           The travulog code and the verilog block are replaced with a single instance
           of the new block generated through the template.
           The process steps of this command are:
                1) Parse the commands line and save TEMPLATE, INFILE, OUTFILE 
                2) Create a moddata obj of INFILE  -> md_old_obj
                3) Parse the CONNECT command and the verilog instance 
                4) Apply the TEMPLATE to the md_old_mod and It print the transformed module on file
                5) Create the parameter related to the new obj using PARAM_FILE
                6) Create the object of the new transformed module -> md_new_obj
                7) If filename of old module don't exist in OUT_DIR copy it there
                8) Substitute all parameter in connection commands an set all connection for the instance
                9) Create the instance of the new module
               10) Substitute the new instance instead of command_block sf.new_verilog_block_list
        """
        # Code list definitions
        key_inline = ["TEMPLATE", "INFILE", "OUTFILE"]
        key_multiline = ["CONNECT"]
        real_line = sf.vblock_start_line + start_line_new_code
        command_block_l_len = len(command_block_l)
        title = False
        ##############################################################################
        #### 1) Parse the htravulog code
        
        # In code_list we will have all command like, using the example in the previous command the
        # code_list should be : 
        #   {"code_list" : [ "TEMPLATE filename_of_output_file", 
        #   "INFILE filename_of_input", "OUTFILE filename_of_output", 
        #   "[IF MAIN_MOD_[IN|OUT|INTERN|PARAM]|NEW_[IN|OUT] ] IN = [prefix_]IN[_suffix]", 
        #   "[IF MAIN_MOD_[IN|OUT|INTERN|PARAM]|NEW_[IN|OUT] ] OUT = [prefix_]OUT[_suffix]"],
        #   "verilog_block": "verilog_instance"}
        raw_code_dict = sf.GetInnerCmdDict(0, command_block_l, "ADD_MODULE_LAYER", htravulog = True)
        raw_code_list = raw_code_dict["code_list"]
        verilog_code = raw_code_dict["verilog_block"]

        # We parse the code list to have a dictionary like:
        # { "TEMPLATE": "filename_of_output_file" ,"INFILE": "filename_of_input", "OUTFILE": "filename_of_output_file", 
        #  "CONNECT": ["[IF MAIN_MOD_[IN|OUT|INTERN|PARAM]|NEW_[IN|OUT|INTERN|PARAM] ] IN = [prefix_]IN[_suffix]",
        #           "[IF MAIN_MOD_[IN|OUT|INTERN|PARAM]|NEW_[IN|OUT|INTERN|PARAM] ] OUT = [prefix_]OUT[_suffix]"]] }
        code_dict = sf.ParseHTVCodeList(real_line, raw_code_list, key_inline, key_multiline, title, linesplit=False)
        sf.dprint(code_dict)
        sf.dprint(verilog_code)

        ##############################################################################
        #### 2)  Create a moddata obj of INFILE  -> md_old_obj
        md_mod_obj = moddata(code_dict["INFILE"], sf.module_prefix, sf.indent)
        md_mod_obj.Analyze()

        ##############################################################################
        #### 3) Parse the CONNECT command and the verilog instance
        
        # This function return a dictionary like:
        # {"module_name": str, "instance_name": str, "param_connections" : { "param" : "connected_param" , ... },
        #  "io_connections": { "signal": "connected_sig", ....}, "indent_int" : int}
        info_dict = GetInstanceInfo(verilog_code, real_line)

        ##############################################################################
        #### 4) Apply the TEMPLATE to the md_old_mod and It print the transformed module on file
        # Set the travulog obj
        tv_obj = sf.templates[code_dict["TEMPLATE"]]["obj"]
        # The name of the new module is deriveed from the name of the file 
        new_module_name = os.path.basename(code_dict["OUTFILE"]).split(".")[0]
        # Name of the parameter related to the new travulog file, derived by its name
        param_name = md_mod_obj.GetParamBaseNoPrefix()

        # Set in the correct template the object to use as BLOCK in the travulog code
        tv_obj.SetModuleFilename("BLOCK", md_mod_obj)
        # Elaborate the template
        datafile = tv_obj.GetElaboratedTemplate(new_module_name, param_name)
        
        sf.last_module_name = new_module_name
        sf.last_param_name = param_name
        sf.last_tv_obj = tv_obj


        fp = open(code_dict["OUTFILE"],"w")
        fp.write(datafile)
        fp.close()

        ############################################################################## 
        #### 5) Create the parameter related to the new obj using PARAM_FILE
        # Elaborate the paramter file
        template_param = tv_obj.GetElaboratedTemplateParams(new_module_name, param_name)
        if template_param != 1:
            sf.templates_param_datafile += template_param
            sf.templates_param_datafile += "\n\n"

        ##############################################################################
        #### 6) Create the object of the new transformed module -> md_new_obj
        md_new_mod_obj = moddata(code_dict["OUTFILE"], sf.module_prefix, sf.indent)
        md_new_mod_obj.Analyze(md_mod_obj)


        ##############################################################################
        #### 7) If filename of old module don't exist in OUT_DIR copy it there
        if not os.path.isfile(sf.output_dir+"/"+os.path.basename(code_dict["INFILE"])):
            source = code_dict["INFILE"]
            dest = sf.output_dir+"/"+os.path.basename(code_dict["INFILE"])
            shutil.copyfile(source, dest)
  
        ##############################################################################
        #### 8) Substitute all parameter in connection commands an set all connection for the instance
        param_dict = { "MAIN_MOD_IN": sf.md_main_mod_obj.GetInputSigNamesList(),
                       "MAIN_MOD_OUT": sf.md_main_mod_obj.GetOutputSigNamesList(),
                       "MAIN_MOD_INTERN": sf.md_main_mod_obj.GetInternSigNamesList(),
                       "MAIN_MOD_PARAM": sf.md_main_mod_obj.GetParameterNamesList(),
                       "MAIN_MOD_ID": sf.md_main_mod_obj.GetParamBaseNoPrefix(),
                       "NEW_IN": md_new_mod_obj.GetInputSigDiffNamesList(),
                       "NEW_OUT":md_new_mod_obj.GetOutputSigDiffNamesList(),
                       "CURRENT_MOD_ID":md_new_mod_obj.GetParamBaseNoPrefix()}

        sf.last_current_mod_id = md_new_mod_obj.GetParamBaseNoPrefix()

        # We save the new signals that are new
        for sig, sig_bit in zip(md_new_mod_obj.GetInputSigDiffNamesList(), md_new_mod_obj.GetInputSigDiffBitsList()):
            if not sig in sf.ADM_new_mod_input_sig.keys():
                sf.ADM_new_mod_input_sig[sig] = sig_bit 
        
        for sig, sig_bit in zip(md_new_mod_obj.GetOutputSigDiffNamesList(), md_new_mod_obj.GetOutputSigDiffBitsList()):
            if not sig in sf.ADM_new_mod_output_sig.keys():
                sf.ADM_new_mod_output_sig[sig] = sig_bit 

        sf.dprint(json.dumps(param_dict, indent=4))
        real_con_command = []
        for connection_statement in code_dict["CONNECT"]:
            for param, sig_list in zip(param_dict.keys(), param_dict.values()):
                if type(sig_list) == list:
                    connection_statement = connection_statement.replace(param, " ".join(sig_list))
                else:
                    connection_statement = connection_statement.replace(param, sig_list)
            real_con_command.append(CompressLineSpaceTabs(connection_statement))
        
        sf.dprint("àààààààààààààààààààààààààààààààààààààààààà")
        sf.dprint(real_con_command)    
        for key,value in zip(info_dict["io_connections"].keys(),info_dict["io_connections"].values()):
            sf.dprint(key+":"+value)

        SetInstanceConnection(md_new_mod_obj, real_con_command, real_line, sf.md_main_mod_obj, info_dict["io_connections"], debug=sf.debug)
        

        ##############################################################################
        #### 9) Create the instance of the new module
        instance_name = md_new_mod_obj.GetModuleNameNoPrefix()
        instance = md_new_mod_obj.GetInstance( instance_name, indent_int)

        ##############################################################################
        #### 6) Substitute the new instance instead of command_block sf.new_verilog_block_list
        del sf.new_verilog_block_list[start_line_new_code:start_line_new_code+command_block_l_len]
        cnt=0
        sf.dprint("ADD_MODULE_LAYER line:%d create this instance:"%int(real_line))
        for instance_line in instance.split("\n"):
            sf.new_verilog_block_list.insert(start_line_new_code+cnt, instance_line)
            sf.dprint(instance_line)
            cnt+=1
        
        return sf.new_verilog_block_list    


    def CreateModule(sf, start_line_new_code,  command_block_l, indent_int):
        """ This function elaborate a code block with this syntax:
           //// CREATE_MODULE new_module_name
           //// OUTFILE filename_of_output_file
           ////
           //// IN sig1 sig2 ...
           //// sigN END_IN
           //// OUT sig1 sig2 ...
           //// sigN END_OUT
                verilog code
           //// END_CREATE_MODULE
           The travulog code and the verilog block are replaced with a single instance
           of the new block.
           The process step of this command are:
                1) It parse the commands line and save io signal
                2) Create a new moddata object for the new module
                3) Use md_main_mod_obj to configure new object with io and internal
                4) Save the complete verilog of the new object in the OUTFILE
                5) Create the instance of the new module
                6) Substitute the new instance instead of command_block sf.new_verilog_block_list
        """
        # Code list definitions
        key_inline = ["OUTFILE"]
        key_multiline = ["IN", "OUT"]
        real_line = sf.vblock_start_line+start_line_new_code
        command_block_l_len = len(command_block_l)
        title = True
        ##############################################################################
        #### 1) Parse the htravulog code
        
        # In code_list we will have all command like, using the example in the previous command the
        # code_list should be : [ "new_module_name", "OUTFILE filename_of_output_file", 
        #   "IN sig1 sig2 ...", "sigN END_IN", "OUT sig1 sig2 ...", "sigN END_OUT" ]
        raw_code_dict = sf.GetInnerCmdDict(0, command_block_l, "CREATE_MODULE", htravulog = True)
        raw_code_list = raw_code_dict["code_list"]
        verilog_code = raw_code_dict["verilog_block"]

        # We parse the code list to have a dictionary like:
        # {'TITLE': "new_module_name", "OUTFILE": "filename_of_output_file", 
        #  "IN": ["sig1","sig2"...,"sigN"], "OUT":["sig1","sig2"...,"sigN"]}
        code_dict = sf.ParseHTVCodeList(real_line, raw_code_list, key_inline, key_multiline, title)
        sf.dprint(code_dict)
        sf.dprint(verilog_code)

        ##############################################################################
        #### 2) Create a new moddata object for the new module
        md_newmod_obj = moddata("", sf.module_prefix, sf.indent)
        md_newmod_obj.SetVerilogBlock(verilog_code)
        md_newmod_obj.SetModuleName(code_dict["TITLE"])
        md_newmod_obj.SetImportList(sf.md_main_mod_obj.GetImportList())

        ##############################################################################
        #### 3) Use md_main_mod_obj to configure new object with io and internal
        if md_newmod_obj.SetSigAsAnotherModuleSig(sf.md_main_mod_obj, code_dict["IN"], sf.IN_ID ) == 1:
            sf.HTVFileError("ERROR4 input signal of %s block aren't in main block %s"%
                    (code_dict["TITLE"], sf.md_main_mod_obj.GetModuleName()))
        
        if md_newmod_obj.SetSigAsAnotherModuleSig(sf.md_main_mod_obj, code_dict["OUT"], sf.OUT_ID ) == 1:
            sf.HTVFileError("ERROR4 input signal of %s block aren't in main block %s"%
                    (code_dict["TITLE"], sf.md_main_mod_obj.GetModuleName()))

        md_newmod_obj.SetInternSigFromOtherModuleSearchingInVerilogCode(sf.md_main_mod_obj )
        
        ##############################################################################
        #### 4) Save the complete verilog of the new object in the OUTFILE
        datafile = md_newmod_obj.GetCompleteVerilog()
        if datafile == "":
            sf.HTVFileError("ERROR in CreateFtBlock, GetCompleteVerilog return empty string, line %d"%
                    start_line_new_block)

        fp = open(code_dict["OUTFILE"],"w")
        fp.write(datafile)
        fp.close()
      
        ##############################################################################
        #### 5) Create the instance of the new module
        instance_name = md_newmod_obj.GetModuleNameNoPrefix()
        instance = md_newmod_obj.GetInstance( instance_name, indent_int)

        ##############################################################################
        #### 6) Substitute the new instance instead of command_block sf.new_verilog_block_list
        del sf.new_verilog_block_list[start_line_new_code:start_line_new_code+command_block_l_len]
        cnt=0
        sf.dprint("CREATE_MODULE line:%d create this instance:"%int(real_line))
        for instance_line in instance.split("\n"):
            sf.new_verilog_block_list.insert(start_line_new_code+cnt, instance_line)
            sf.dprint(instance_line)
            cnt+=1
        
        return sf.new_verilog_block_list    

    ###########################################################################################################
    # ElaborateVerilogBlock support functions
    ###########################################################################################################
    def EVBGetCodePattern(sf, verilog_code_list, cmd_list):
        """ It Analyze sf.main_mod_datafile and it return a list of dict:
        [{"nesting":0, "name":"CREATE_MODULE", "start_line":10, "end_line":30}, ...]
        nesting -> contain 0 if the command haven't nested command, 1 if there is a nested command
                        2 if there are 2 nested command etc
        name -> keyword name od command (e.g. CREATE_MODULE)
        verilog_code -> code from which create a pattern
        indent_int -> indentation of the command
        """
        cmd_list_of_dict = []

        nesting = 0
        cmd_list_of_dict_cnt = 0
        in_a_command = False
        sf.lineno = 0
        end_line = len(verilog_code_list)

        while sf.lineno < end_line:
            line = verilog_code_list[sf.lineno]
            for keyword in cmd_list:
                if re.match("^.*[^_]"+keyword+".*$", line)!=None or re.match("^"+keyword+".*$", line)!=None:
                    if in_a_command:
                        nesting+=1
                    sf.dprint("      "*nesting+" Start %s"%keyword,sf.lineno)
                    if cmd_list_of_dict_cnt > 0:
                        if cmd_list_of_dict[cmd_list_of_dict_cnt]["end_line"] == 0:
                            if nesting == 0:
                                line1 = cmd_list_of_dict[cmd_list_of_dict_cnt]["start_line"]
                                name = cmd_list_of_dict[cmd_list_of_dict_cnt]["name"]
                                sf.HTVFileError("Line %d, You miss END_%s"%(line1, name))
                    cmd_list_of_dict_cnt = len(cmd_list_of_dict)
                    line_indent = GetStringIndent(line, sf.indent_int)
                    cmd_list_of_dict.append({"nesting":nesting, "name":keyword, "start_line":sf.lineno, 
                                             "end_line":0, "indent_int":line_indent})
                    in_a_command=True
            
            for keyword in cmd_list:
                if re.match("^.*END_"+keyword+".*$", line)!=None or re.match("^END_"+keyword+".*$", line)!=None:
                    sf.dprint("      "*nesting+" END %s"%keyword,sf.lineno)
                    if cmd_list_of_dict[cmd_list_of_dict_cnt]["name"] != keyword:
                        key = cmd_list_of_dict[cmd_list_of_dict_cnt]["name"]
                        sf.HTVFileError("Line %d, we need END_%s"%(int(sf.lineno-1),key))
                    cmd_list_of_dict[cmd_list_of_dict_cnt]["end_line"] = sf.lineno
                    if in_a_command and nesting > 0: 
                        nesting-=1
                        cmd_list_of_dict_cnt -=1
                    if nesting == 0:
                        in_a_command=False
            
            if nesting < 0:
                sf.HTVFileError("Line %d, extra END"%int(sf.lineno+1))

            sf.lineno += 1
        # control
        for dic in cmd_list_of_dict:
            if dic["end_line"] == 0:
                sf.HTVFileError("Line %d, END key not found"%sf.lineno)
        
        cmd_list_of_dict.sort(key = lambda item: item.get("nesting"), reverse=True)
        sf.dprint(json.dumps(cmd_list_of_dict, indent=4))

        return cmd_list_of_dict


    ###########################################################################################################
    # Elaborate Before Module functions
    ###########################################################################################################
    def EBMSetImport(sf, code_list):
        """ Save the filename of the htravulog package and it import the package variable.
        Import should be like:
        //// IMPORT filename
        The filename should contain:
            IN_DIR directory1
            OUT_DIR directory2
            TEMPLATE id 
                FILE filename1
                PARAM_FILE filename2
                PKG_FILE filename3
            END_TEMPLATE
            MODULE_PREFIX stringa
        
        set sf.input_dir = directory1
        set sf.output_dir = directory2
        set sf.templates = { "id" : {"file":filename1, "param_file":filename2, "pkg_file":filename, "obj":travulog_obj} }
        set sf.module_prefix = stringa

        """
        # Code controls
        if len(code_list) != 2:
            sf.HTVFileError("Line %d, correct command is \"IMPORT filename\""%sf.lineno)
        
        sf.htpkg_filename = sf.VerifyAndGetAbsPath(code_list[1], "Line %d"%sf.lineno)

        # We save setting from the package
        fp = open(sf.htpkg_filename,"r")
        sf.dprint_fname = sf.htpkg_filename
        pkg_fileline_list = fp.read().split("\n") 
        pkg_fileline_num = len(pkg_fileline_list)
        pkg_lineno = 0
        cmdflag = [0,0,0,0,0,0]
        while pkg_lineno < pkg_fileline_num:
            cmd_list = sf.GetHtravulogCode(pkg_fileline_list[pkg_lineno]).split(" ")
            cmd = cmd_list[0]
            if cmd == "IN_DIR":
                sf.CheckCodeListElements(cmd_list," In directory set with \"IN_DIR directory\","
                                                    "you miss directory line %d"%pkg_lineno, 2)
                VerifyDir(cmd_list[1], "Pkg file %s, line %d "%(sf.htpkg_filename, pkg_lineno))
                sf.input_dir = cmd_list[1]
                sf.dprint("[pkg %s] Set IN_DIR = %s"%(sf.htpkg_filename,sf.input_dir), pkg_lineno)
                cmdflag[0] = 1
                 
            elif cmd == "OUT_DIR":
                sf.CheckCodeListElements(cmd_list," in directory set with \"out_dir directory\","
                                                    "you miss directory line %d"%pkg_lineno, 2)
                VerifyDir(cmd_list[1], "pkg file %s, line %d "%(sf.htpkg_filename, pkg_lineno))
                sf.output_dir = cmd_list[1]
                sf.dprint("[pkg %s] set out_dir = %s"%(sf.htpkg_filename,sf.output_dir), pkg_lineno)
                cmdflag[1] = 1
            
            elif cmd == "PKG_FILE":
                sf.CheckCodeListElements(cmd_list," in directory set with \"PKG_FILE file\","
                                                    "you miss directory line %d"%pkg_lineno, 2)
                VerifyFile(line_split[1], "Pkg file %s, line %d "%(sf.htpkg_filename, pkg_lineno))
                sf.pkg_file = cmd_list[1]
                sf.dprint("[pkg %s] set pkg_file = %s"%(sf.htpkg_filename,sf.pkg_file), pkg_lineno)
                cmdflag[2] = 1
            
            elif cmd == "PKG_OUT_FILE":
                sf.CheckCodeListElements(cmd_list," in directory set with \"PKG_OUT_FILE file\","
                                                    "you miss directory line %d"%pkg_lineno, 2)
                VerifyFile(line_split[1], "Pkg file %s, line %d "%(sf.htpkg_filename, pkg_lineno))
                sf.pkg_out_file = cmd_list[1]
                sf.dprint("[pkg %s] set pkg_file = %s"%(sf.htpkg_filename,sf.pkg_file), pkg_lineno)
                cmdflag[3] = 1

            elif cmd == "TEMPLATE":
                cmd_lines_list = sf.GetInnerCmdLinesList(pkg_lineno, pkg_fileline_list, "TEMPLATE", compress=True)
                # We verify that after TEMPLATE  there is only the id
                if len(cmd_lines_list[0].split(" ")) != 1:
                    sf.HTVFileError("Pkg file %s, line %d "%(sf.htpkg_filename, pkg_lineno))
                template_id = cmd_lines_list[0]
                sf.templates[template_id] = {}
                keyflag = [0,0]
                for line in cmd_lines_list[1:]:
                    line_split = line.split(" ")
                    if line_split[0] == "FILE":
                        VerifyFile(line_split[1], "Pkg file %s, line %d "%(sf.htpkg_filename, pkg_lineno))
                        sf.templates[template_id]["file"] = line_split[1]
                        keyflag[0] = 1

                    elif line_split[0] == "PARAM_FILE":
                        VerifyFile(line_split[1], "Pkg file %s, line %d "%(sf.htpkg_filename, pkg_lineno))
                        sf.templates[template_id]["param_file"] = line_split[1] 
                        keyflag[1] = 1

                    else:
                        sf.HTVFileError("Pkg file %s, line %d , %s isn't a keyword"
                                    %(sf.htpkg_filename, pkg_lineno, line_split[0]))

                if keyflag != [1,1]:
                    sf.HTVFileError("Pkg file %s, line %d , you miss one of FILE,"
                                "PARAM_FILE or PKG_FILE"%(sf.htpkg_filename, pkg_lineno))
                
                cmdflag[4] = 1  
                sf.dprint("[pkg %s] Set TEMPLATE = %s"%(sf.htpkg_filename,json.dumps(sf.templates, indent=4)), pkg_lineno)
                sf.templates[template_id]["obj"] = travulog(sf.templates[template_id]["file"], 
                                                            sf.templates[template_id]["param_file"],
                                                            {}, sf.module_prefix, sf.indent)

            elif cmd == "MODULE_PREFIX":
                sf.CheckCodeListElements(cmd_list," Module prefix set with \"MODULE_PREFIX directory\","
                                                                    "you miss prefix line%d"%pkg_lineno, 2)
                sf.module_prefix = cmd_list[1]
                sf.dprint("[pkg %s] Set MODULE_PREFIX = %s"%(sf.htpkg_filename,sf.module_prefix), pkg_lineno)
                cmdflag[5] = 1

            pkg_lineno += 1
        
        if cmdflag != [1,1,1,1,1,1]:
            sf.HTVFileError("[pkg %s] you should set IN_DIR,OUT_DIR,TEMPLATE and MODULE_PREFIX"%(sf.htpkg_filename))




    def EBMSetNewModuleName(sf, code_list):
        """ Save the module name from command:
        //// NEW_MODULE_NAME string
        
        set sf.new_module_name = string
        """
        # Code controls
        if len(code_list) != 2:
            sf.dprint(json.dumps(code_list, indent=4))
            sf.HTVFileError("Line %d, correct command is \"//// NEW_MODULE_NAME stringa\""%sf.lineno)
        
        sf.new_module_name = code_list[1]
    
    def EBMSetNewModuleFilename(sf, code_list):
        """ Save the module filename from command:
        //// NEW_MODULE_FILE string
        
        set sf.new_module_filename = string
        """
        # Code controls
        if len(code_list) != 2:
            sf.dprint(json.dumps(code_list, indent=4))
            sf.HTVFileError("Line %d, correct command is \"//// NEW_MODULE_FILE stringa\""%sf.lineno)

        sf.new_module_filename = sf.SubstitutePkgVar(code_list[1])
        VerifyDir(os.path.dirname(sf.new_module_filename), "NEW_MODULE_FILE %s has wrong directory"%sf.new_module_filename)
        

    ###########################################################################################################
    # Support functions
    ###########################################################################################################

    def ParseHTVCodeList(sf, real_text_start_line, code_list, key_inline, key_multiline, title = False, linesplit=True):
        """ Take a list of htravulog commands like:
        ['cv32e40p_program_counter_definition',
         'OUTFILE OUT_DIR/cv32e40p_program_counter_definition.sv', 'IN m_exc_vec_pc_mux_i', 
         'pc_set_i pc_mux_i', 'END_IN', 'OUT branch_addr_n', 'csr_mtvec_init_o', 'END_OUT']
        In this case the key_inline is: ["OUTFILE"]
        The key_multiline is: ["IN", "OUT"]
        title = True -> this means that the first element of the list not empty should be considered
        This means that key_inline indicates the key with all argument on the same line,
        while key_multiline indicates the key commands that needs a END_ termination and
        could be multiline.
        The function return a dictionary like:
        {"TITLE" : "cv32e40p_program_counter_definition",
         "OUTFILE": "OUT_DIR/cv32e40p_program_counter_definition.sv", 
         "IN": [ 'm_exc_vec_pc_mux_i', 'pc_set_i pc_mux_i'] ,
         "OUT": ['OUT branch_addr_n', 'csr_mtvec_init_o']}
        """
        code_dict = {}
        code_list_cnt = 0
        code_list_len = len(code_list)
        if title:
            while code_list_cnt < code_list_len:
                line = code_list[code_list_cnt]
                real_line_cnt = real_text_start_line + code_list_cnt
                # Verify that there aren't other key in the title
                for key in key_inline:
                    if IsStartKey(line,key):
                        sf.HTVFileError("Lack of title line %d, key %s"%(real_line_cnt,key))
                for key in key_multiline:
                    if IsStartKey(line,key) or IsEndKey(line, key):
                        sf.HTVFileError("Lack of title line %d, key %s"%(real_line_cnt, key))
                if line != "" and len(line.split(" "))==1:
                    code_dict["TITLE"] = line
                    break
                code_list_cnt += 1
        
        while code_list_cnt < code_list_len:
            line = sf.SubstitutePkgVar(code_list[code_list_cnt])
            line_list = line.split(" ")
            line_el_n = len(line_list)
            real_line_cnt = real_text_start_line + code_list_cnt
            # Inline commands
            for key in key_inline:
                if IsStartKey(line, key):
                    if line_el_n != 2:
                        sg.HTVFileError("Inline command need one argument line: %d"%real_line_cnt)
                    code_dict[key] = line_list[1] 
                    break

            else:
                # Multiline commands
                for key in key_multiline:
                    if IsStartKey(line, key):
                        code_dict[key] = []
                        if line_el_n > 1:
                            if linesplit:
                                code_dict[key] += line_list[1:]
                            else:
                                code_dict[key].append(" ".join(line_list[1:]))
                        code_list_cnt += 1
                        while code_list_cnt < code_list_len:
                            line = sf.SubstitutePkgVar(code_list[code_list_cnt])
                            line_list = line.split(" ")
                            line_el_n = len(line_list)
                            real_line_cnt = real_text_start_line + code_list_cnt
                            if IsEndKey(line, key):
                                if line_el_n > 1: 
                                    if line_list[-1] != "END_"+key:
                                        sf.HTVFileError("END_%s should be at the end of "
                                                "line, line %d"%(key,real_line_cnt))
                                    if linespit:
                                        code_dict[key] += line_list[:-1]
                                    else:
                                        code_dict[key].append(" ".join(line_list[:-1]))
                                else:
                                    break
                            else:
                                if linesplit:
                                    code_dict[key] += line_list
                                else:
                                    code_dict[key].append(" ".join(line_list))
                            code_list_cnt+=1


            code_list_cnt += 1
        # END WHILE
        return code_dict

    def SubstitutePkgVar(sf, line):
        line = line.replace("OUT_DIR", sf.output_dir)
        line = line.replace("IN_DIR", sf.input_dir)
        line = line.replace("MODULE_PREFIX", sf.module_prefix)
        return line

    
    def CheckCodeListElements(sf, code_list, error_str, element_num, element_num_max=0):
        """ Verify that a list have a number of element equal to element_num
        If element_num_max is specified, the number of element of the list should be 
        between element_num and element_num_max
        """
        if element_num_max ==0:
            if len(code_list) != element_num:
                sf.HTVFileError(error_str)
        else:
            if len(code_list) <element_num or len(code_list) > element_num_max:
                sf.HTVFileError(error_str)
        return

    def GetInnerCmdDict(sf, start_line, text, keyword, htravulog = False):
        """ Return formatted command statement.
        Text can be both a text or a text list
        The typical command lines can be :

        //// CONNECT  IF MAIN_MODULE_IN IN = {IN , IN , IN }
        ////          IF NEW_IN IN = IN[MAIN_MODULE_PARAM_ID_PRCODE]
        ////          OUT = OUT_tr
        //// END_CONNECT
        The funtion return:
        {"code_list" : ["IF MAIN_MODULE_IN IN = {IN , IN , IN }", "IF NEW_IN IN = IN[MAIN_MODULE_PARAM_ID_PRCODE", "OUT = OUT_tr" ],
         "verilog_block" : "" }

        """
        cmd_dict = {"code_list":[], "verilog_block":""}
        inner_cmd = sf.GetInnerCmdLinesList(start_line, text ,keyword, htravulog)
        for line in inner_cmd:
            if sf.IsHtravulogCode(line):
                new_line = sf.GetHtravulogCode(CompressLineSpaceTabs(line))
                cmd_dict["code_list"].append(new_line)
            else:
                cmd_dict["verilog_block"] += line + "\n"
        
        return cmd_dict  

    def GetInnerCmdLinesList(sf,start_line, text_list ,keyword, htravulog = False, compress=False):
        """ Return command statement between keyword and END_keyword:
        A typical text is (start_line = 10, keyword="ADD_MODULE_LAYER"):

        10 //// ADD_MODULE_LAYER
        11 //// TEMPLATE ft_template
        12 //// INFILE OUT_DIR/cv32e40p_program_counter_definition.sv
        13 //// OUTFILE OUT_DIR/cv32e40p_program_counter_definition_ft.sv
        14     verilog code
        ..
        50 //// END_ADD_MODULE_LAYER
        
        The function return:
        ["//// TEMPLATE ft_template",
        "//// INFILE OUT_DIR/cv32e40p_program_counter_definition.sv",
        "//// OUTFILE OUT_DIR/cv32e40p_program_counter_definition_ft.sv",
        "verilog_code"]
        
        TEMPLATE id
            FILE filename
            PARAM_FILE filename
        END_TEMPLATE
        The function return :
        [ "id" , "FILE filename", "PARAM_FILE filename" ]
        """
        if type(text_list) == list:
            realtext_list = text_list
        else:
            realtext_list = text_list.split("\n")
        
        if start_line > len(realtext_list):
            sf.HTVFileError("In GetInnerCmdLinesList, line %d is too high"%start_line)
            
        realtext_list = realtext_list[start_line:]

        if not keyword in realtext_list[0]:
            sf.HTVFileError("Keyword %s isn't in the first line of the given text"%keyword)

        inner_cmd_lines_list = []
        nested_cnt=0
        # Here we take the first line, and save the strings at the right of keyword
        if len(realtext_list[0].split(" "))>1:
            title = realtext_list[0].split(keyword)[1]
            if htravulog:
                title = sf.HTKEY + " "+title
            if compress:
                inner_cmd_lines_list.append(CompressLineSpaceTabs(title))
            else:
                inner_cmd_lines_list.append(CompressLineSpaceTabs(title))

        for line in realtext_list[1:]:
            if re.match("^.*[^_]"+keyword+".*$", line)!=None or re.match("^"+keyword+".*$", line) != None  :
                nested_cnt+=1 

            if not "END_"+keyword in line:
                if compress:
                    inner_cmd_lines_list.append(CompressLineSpaceTabs(line))
                else:
                    inner_cmd_lines_list.append(line)
            elif nested_cnt>0:
                nested_cnt-=1
            else:
                break
        else:
            sf.HTVFileError("End string \"END_%s\" not found"%keyword)

        return inner_cmd_lines_list
    

    ###########################################################################################################
    # Minor support functions
    ###########################################################################################################
    def IsHtravulogCode(sf, line):
        return re.match(sf.HTPATTERN, CompressLineSpaceTabs(line))

    def GetHtravulogCode(sf, line):
        # "       //// OUTFILE OUT_DIR/cv32e40p_program_counter_definition_ft.sv"
        # became 
        # "OUTFILE OUT_DIR/cv32e40p_program_counter_definition_ft.sv"
        return CompressLineSpaceTabs(line).replace(sf.HTKEY, "")

    def HTVFileError(sf, stringa):
        print("%s, %s"%(sf.ErrorBaseStr, stringa))
        exit(-1)

    def VerifyAndGetAbsPath(sf, filename, error_str):
        if not os.path.isfile(filename):
            if os.path.isfile(sf.htravulog_dirname+"/"+filename):
                return sf.htravulog_dirname+"/"+filename
            else:
                sf.HTVFileError("%s, Filename %s don't exist, give relative path to %s dir or absolute path"%(error_str,filename,sf.htravulog_dirname))
    
    def dprint(sf,stringa, lineno=""):
        if sf.debug:
            if lineno == "":
                print("[file %s, line %d]"%(sf.dprint_fname,sf.lineno), end="")
            else:
                print("[file %s, line %d]"%(sf.dprint_fname,lineno), end="")
            print("     %s"%(stringa))
        return 




htv = htravulog("./test/arch/cv32e40p_if_stage.sv")
htv.ElaborateHiddenTravulog()
