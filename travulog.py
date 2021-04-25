#!/usr/bin/python3
import sys
import os
import re
import json

from moddata import *
#  GetInnerCommand(data_lines, lineno, key):
#  GetDeclarationForeach(block, inout, command, cmd2, lineno, indent):
#  GetPrefixSuffix(what, sequence, key, lineno):
#  SetSignalElaborationInstance(block_obj, siglist, inoutpar, after_equal, signal_elab, lineno):
#  GetCmdInstance(block_obj,  command, instance_name, lineno, indent_level):
#  GetInstanceForeach(block_obj, model_data, inout, lineno,indent):
#  GetOpUnroll(line_strip, start, end, op, sig, lineno, indent):
#  GetOpForeach(line_strip, block_obj, inout, op, sig, lineno, indent):
#  GetStringIndent( stringa, indent=1):
#  travulog class
#     __init__(sf, template_filename, template_params_filename, module_filename_dict = {},  module_prefix="", indent="        "):
#     SetModuleFilename(sf, block_id, md_obj):
#           Permette di settare l'oggetto moddata relativo all'id block_id che viene utilizzato all'interno del
#           travulog per indicare il blocco da usare
#     GetIndent(sf, indent_level=1):
#     GetElaboratedTemplate(sf,module_name, param_name):
#           Utilizza GetElaboratedTravulog per elaborare il file template del nuovo blocco e lo ritorna
#     GetElaboratedTemplateParams(sf,module_name, param_name):
#           Utilizza GetElaboratedTravulog per elaborare il file dei parametri settato in __init__ e lo ritorna
#     GetElaboratedTravulog(sf, module_name, param_name):
#           Elabora un file Travulog utilizzando le proprietà dei vari moduli settati con SetModuleFilename
#           ritornando il file trasformato.


def GetInnerCommand(data_lines, lineno, key):
    """
     This function return all text between lineno and the first occurrence
     of key, data_lines is a list of lines
    """
    i=lineno+1
    command=""
    while not key in data_lines[i]:
        command+=data_lines[i].strip() + "\n"
        i+=1
        if i > len(data_lines):
            print("ERROR at line %d end keyword %s not found" % lineno, key)
            exit(-1)
    return [command,i+1]

def GetDeclarationForeach(block, inout, command, cmd2, lineno, indent):
    """
     This function create a declaration foreach IN, OUT or both of a block.
     Cycling along input or/and output SIGNAME and BITINIT are substituted in "command" string
    """
    data=""
    if inout == "IN" or inout == "IN_OUT":
        for sig,bit_dict in zip(block.GetInputSigNamesList(), block.GetInputSigBitsList()):
            ok=1
            if "NOT" in cmd2.keys():
                if sig in cmd2["NOT"]:
                    ok=0
            if ok==1:
                data += indent
                bitdef = CreateBitsDefinition(bit_dict)
                data+= command.replace("INOUT","input").replace("SIGNAME",sig).replace("BITINIT",bitdef)

    if inout == "OUT" or inout == "IN_OUT":
        for sig,bit_dict in zip(block.GetOutputSigNamesList(), block.GetOutputSigBitsList()):
            ok=1
            if "NOT" in cmd2.keys():
                if sig in cmd2["NOT"]:
                    ok=0
            if ok==1:
                data += indent
                bitdef = CreateBitsDefinition(bit_dict)
                data+= command.replace("INOUT","output").replace("SIGNAME",sig).replace("BITINIT",bitdef)

    if inout != "OUT" and inout != "IN" and inout != "IN_OUT":
        print("ERROR line %d, INOUT variable can be only IN,OUT or IN_OUT" % lineno)

    data += "\n"
    return data

def GetPrefixSuffix(what, sequence, key, lineno):
    #############################################################################
    # This function analyze sequence list and it find prefix and suffix of key
    # the general format is "prefix key suffix", key can also don't exist, but
    # should be at least a word. We could have the following case:
    #   prefix key
    #   key suffix
    #   suffix
    #   prefix key suffix
    #############################################################################
    prefix=""
    suffix=""
    if what == key:
        if len(sequence) == 3: # we have prefix and suffix
            if sequence[1] == key:
                prefix = sequence[0]
                suffix = sequence[2]
            else:
                print("ERROR : line %d second argument of \"%s =\" should be %s " % lineno,key,key)
                exit(-1)
        elif len(sequence) == 2:
            if sequence[0] == key:
                suffix = sequence[1]
            elif sequence[1] == key:
                prefix = sequence[0]
            else:
                print("ERROR : line %d, when you give two argument first or second should be %s" % lineno,key)
                exit(-1)
        elif len(sequence) == 1 and sequence[0] != "IN" and sequence[0] != "OUT" and sequence[0] != "PARAM":
            prefix="UNIQUE"
            suffix = sequence[0]
        elif len(sequence) == 1:
            prefix=""
            suffix=""
        else:
            print("ERROR : line %d, you should said how to connect signals" % lineno)
            exit(-1)
    return [prefix, suffix]


def  SetSignalElaborationInstance(block_obj, siglist, inoutpar, after_equal, signal_elab, lineno):
    """
     This function elaborate a travulog instance statement like:
       OUT = OUT _to_vote[i]
     Argument are:
     block -> It is the dict module info ot the block of which create instance
     siglist -> This is the list of signals of which apply the prefix and suffix
     inotpar -> This argument can be "IN" "OUT" or "PARAM", it indicated the type of signal
               this information is used to verify if the siglist signals are correct
    """

    if inoutpar != "IN" and inoutpar != "OUT" and inoutpar != "PARAM":
        print("ERROR line %d, only IN, OUT and PARAM is possible"%lineno)
        exit(-1)
    sigdict = {"IN":block_obj.GetInputSigNamesList(),  "OUT":block_obj.GetOutputSigNamesList(), "PARAM":block_obj.GetParameterNamesList()}
    pre_suf = GetPrefixSuffix(inoutpar, after_equal, inoutpar,lineno)
    append_list = []
    flag=0
    for sig in siglist:
        if not sig in sigdict[inoutpar]:
            print("WARNING line %d, signal %s isn't an %s signal of set block %s" %(lineno, sig, inoutpar, block_obj.GetModuleName()))
            #print("%s signals of %s block are:"% (inoutpar,block['module']))
            #print(json.dumps(sigdict[inoutpar], indent=4))
            #exit(-1)
        if len(signal_elab[inoutpar])==0:
            append_list.append(sig)
            flag=1
        else:
            thereis=0
            for data in signal_elab[inoutpar]:
                for sig1 in data[0]:
                    if sig == sig1:
                        thereis =1

            if not thereis:
                append_list.append(sig)
                flag=1

    if flag==1:
        signal_elab[inoutpar].append([append_list,pre_suf])

    return signal_elab


def GetCmdInstance(block_obj,  command, instance_name, lineno, indent_level):
    """
     This function return an instance of a block, using "command" to correctly connect
     instance, instance_name is the name of the instance while block is a
     dictionary with info about the module
    """
    cmd_line=command.strip().split("\n")
    data=""
    signal_elab  = {"OUT":[],"IN":[],"PARAM":[]}
    sigdict = {"IN":block_obj.GetInputSigNamesList(),  "OUT":block_obj.GetOutputSigNamesList(), "PARAM":block_obj.GetParameterNamesList()}

    for cmd in cmd_line:
        cmd_list=cmd.strip().split(" ")
        if cmd_list[0] == "IF":
            if not "IN" in cmd and not "OUT" in cmd and not "PARAM" in cmd and not "=" in cmd:
                print("ERROR line %d, IF without IN,OUT or PARAM keyword"%lineno)
                exit(-1)
            else:
                before_equal=cmd.split("=")[0].strip()
                what = before_equal.strip().split(" ")[-1]
                apply_to_list = before_equal.strip().split(" ")[1:-1]
                equal_to=cmd.split("=")[1].strip()
                sequence = equal_to.split(" ")
                if what == "IN" or what == "OUT" or what == "PARAM":
                    signal_elab = SetSignalElaborationInstance(block_obj, apply_to_list,what, sequence, signal_elab, lineno)
                else:
                    print("ERROR, line "+str(lineno)+", use IN, OUT and PARAM command only, not -"+what+"-")
                    exit(-1)
        elif "=" in cmd:
                what=cmd.split("=")[0].strip()
                equal_to=cmd.split("=")[1].strip()
                sequence = equal_to.split(" ")
                if what == "IN" or what == "OUT" or what == "PARAM":
                    signal_elab = SetSignalElaborationInstance(block_obj, sigdict[what],what, sequence, signal_elab, lineno)
                else:
                    print("ERROR, line "+str(lineno)+", use IN, OUT and PARAM command only, not -"+what+"-")
                    exit(-1)

    module_name = block_obj.GetModuleName()
    parameter = block_obj.GetParameterNamesList()
    
    input_port_connection_list= []
    output_port_connection_list= []
    in_n=0
    for sig in block_obj.GetInputSigNamesList():
        for sig_tc_list in signal_elab["IN"]:
            for sig_tc in sig_tc_list[0]:
                if sig == sig_tc:
                    in_n+=1
                    if sig_tc_list[1][0] == "UNIQUE":
                        input_port_connection_list.append(sig_tc_list[1][1])
                    else:
                        input_port_connection_list.append(sig_tc_list[1][0]+sig+sig_tc_list[1][1])

    for sig in block_obj.GetOutputSigNamesList():
        for sig_tc_list in signal_elab["OUT"]:
            for sig_tc in sig_tc_list[0]:
                if sig == sig_tc:
                    if sig_tc_list[1][0] == "UNIQUE":
                        output_port_connection_list.append(sig_tc_list[1][1])
                    else:
                        output_port_connection_list.append(sig_tc_list[1][0]+sig+sig_tc_list[1][1])

    #data += GetInstance(module_name, instance_name, parameter, vect1, vect2, indent, [in_n])
    block_obj.SetInputPortConnections(input_port_connection_list)
    block_obj.SetOutputPortConnections(output_port_connection_list)
    data += block_obj.GetInstance(instance_name, indent_level)

    return data

def GetInstanceForeach(block_obj, model_data, inout, lineno,indent):
    """
     Starting from a verilog code with some variable this function return
     a new code with variable substituted.
     SIGNAME -> name of the signal to vote
     INDEX -> error correction and detection are saved as vectors, for these
               reason each voter will have a number used to address these vectors
     BITNUMBER -> number of bits of signal to vote
     VOTER_NAME -> name of the instance of the voter
    """
    names=[]
    bits=[]
    if inout == "IN" or inout == "IN_OUT":
        names = block_obj.GetInputSigNamesList()
        bits = block_obj.GetInputSigBitsList()
    if inout == "OUT" or inout == "IN_OUT":
        names += block_obj.GetOutputSigNamesList()
        bits += block_obj.GetOutputSigBitsList()
    if inout!="IN" and inout != "OUT" and inout !="IN_OUT":
        print("ERROR at line %d, %s is wrong, only IN, OUT or IN_OUT can be used "%lineno, inout)
        exit(-1)
   
    index=0
    instance = ""
    for sig,bit_dict in zip(names, bits):
        data=model_data
        # Substitute signal name
        data = data.replace("SIGNAME",sig)
        # Substitute the index of output for error detection and correction signals
        data = data.replace("INDEX", str(index))
        if bit_dict["N0UP"] == "1" and bit_dict["N0DW"] == "0":
            data = data.replace("BITNUMBER","1")
        else:
            data = data.replace("BITNUMBER",str(int(bit_dict["N0UP"])+1))

        ndata=""
        for line in data.split("\n"):
            if "." in line:
                ndata = ndata + indent + "         "+ line + "\n"
            else:
                ndata = ndata + indent + line + "\n"
        instance += ndata
        index += 1

    return instance

def GetOpUnroll(line_strip, start, end, op, sig, lineno, indent):
    """
    """
    if start > end or start==end:
        print("Error line %d, start (%d) should be less then end (%d)"%lineno,start,end)
        exit(-1)
    unroll=indent
    words=line_strip.split(" ")
    indent_word = ""
    i=0
    while i < len(words):
        if words[i] == "OP_UNROLL":
            i+=5
            cnt=int(start)
            indent_word = len(unroll.strip())*" "
            operation= " " +sig + "["+str(cnt)+"]\n"
            cnt+=1
            while cnt < int(end)-1:
                operation += indent + indent_word+ op + " " + sig + "["+str(cnt)+"]\n"
                cnt+=1
            operation += indent + indent_word+ op + " " + sig + "["+str(cnt)+"];\n"
            unroll += operation

        else:
            unroll += words[i] + " "
        i+=1

    return unroll

def GetOpForeach(line_strip, block_obj, inout, op, sig, lineno, indent):
    unroll=indent
    words=line_strip.split(" ")
    indent_word = ""
    i=0
    while i < len(words):
        if words[i] == "OP_FOREACH":
            i+=4
            names=[]
            bits=[]
            if inout == "IN" or inout == "IN_OUT":
                names = block_obj.GetInputSigNamesList()
                bits = block_obj.GetInputSigBitsList()
            if inout == "OUT" or inout == "IN_OUT":
                names += block_obj.GetOutputSigNamesList()
                bits += block_obj.GetOutputSigBitsList()
            if inout!="IN" and inout != "OUT" and inout !="IN_OUT":
                print("ERROR at line %d, %s is wrong, only IN, OUT or IN_OUT can be used "%lineno, inout)
                exit(-1)
            indent_word = len(unroll.strip())*" "
            if op == "//" :
                if len(unroll.strip())>=2:
                    indent_word = (len(unroll.strip())-2)*" "
                else:
                    indent_word = ""
                
            indent_word = indent + indent_word
            end_str="\n"
            if len(sig.replace("SIGNAME",names[0]))*len(names) < 50:
                end_str = ""
                indent_word = ""
            
            operation= " " + sig.replace("SIGNAME",names[0]).replace("INDEX","0") + end_str
            cnt=1
            while cnt < len(names)-1:
                operation += indent_word+ op + " " + sig.replace("SIGNAME",names[cnt]).replace("INDEX",str(cnt)) + end_str
                cnt+=1
            operation += indent_word+ op + " " + sig.replace("SIGNAME",names[cnt]).replace("INDEX",str(cnt)) 
            unroll += operation

        else:
            unroll += words[i] + " "
        i+=1
    
    unroll += "\n"

    return unroll


def GetStringIndent( stringa, indent=1):
    #######################################################################
    # Find the current indentation of "stringa", this
    # function return the number of space before the first letter
    #######################################################################
    endindent=0
    indent_cnt=0
    for letter in stringa:
        if not endindent:
            if letter==" ":
               indent_cnt+=1
            else:
                return indent_cnt//indent


class travulog:
    def __init__(sf, template_filename, template_params_filename, module_filename_dict = {},  module_prefix="", indent="        "):
        """ 
        module_filename_dict -> is a dict like { "BLOCK": "path/to/module1.sv", "BLOCK2":"path/to/module2.sv" }
                    the name BLOCK and BLOCK2 can be used inside travulog to refer to that block data
        template_filename -> filename of the template to use for the creation of new blocks, this template is 
                    writte in verilog with travulog insertion
        package_filename -> package filename, written as template_filename but containing only parameter definition
        indent -> indent unit (tab)
        """
        sf.mod_fname_dict = module_filename_dict
        sf.indent = indent
        sf.template_params_fname = template_params_filename
        sf.template_fname = template_filename
        sf.filename = sf.template_fname
        sf.mod_prefix= module_prefix

        # Find module data using moddata class
        sf.mod_obj_dict = {}
        if module_filename_dict != {}:
            for mod_fname_name, mod_fname_filename in zip(module_filename_dict.keys(),module_filename_dict.values()):
                sf.mod_obj_dict[mod_fname_name] = moddata(mod_fname_filename, sf.mod_prefix)
                sf.mod_obj_dict[mod_fname_name].Analyze()

    ######################################################################################################
    # SET Functions
    ######################################################################################################
    def SetModuleFilename(sf, block_id, md_obj):
        sf.mod_obj_dict[block_id] = md_obj

    ######################################################################################################
    # GET Functions
    ######################################################################################################

    def GetIndent(sf, indent_level=1):
        return sf.indent*indent_level


    def GetElaboratedTemplate(sf,module_name, param_name):
        sf.filename = sf.template_fname
        return sf.GetElaboratedTravulog(module_name, param_name)

    def GetElaboratedTemplateParams(sf,module_name, param_name):
        if sf.template_params_fname == "":
            return 1
        sf.filename = sf.template_params_fname
        return sf.GetElaboratedTravulog(module_name, param_name)

    def GetElaboratedTravulog(sf, module_name, param_name):
        """
         This function start from a template file that create a FT structure of a non 
         FT block, in this file will be many uppercase variable that should be substitute by 
         block of autogenerated code. This autogenerated code depends by arguments of this function
         These are parameter that wil be substitute:
         Global variable , this variable are substitute before elaboration in all file
        -- MODULE_NAME -> Name of the module
        -- PARAM_NAME -> there are some parameters used in verilog to change FT behaviour
                           this parameter is the base name of these parameters
        -- block_name_MODNAME -> name of the block
        
         Elaboration blocks, elements in this block will be cloned for all in or out signal
        -- PARAMETER_DECLARATION block_name -> declare the same parameter of block_name module
        -- DECLARATION_FOREACH block_name inout    
               declaration_command
           END_DECLARATION -> cycle on block_name input (if inout=IN) or output 
                           (if inout=OUT) or both (if inout=IN_OUT) and substitute follow variable:
                           INOUT -> if the signal is an input INOUT="input", if it is an output INOUT="output"
                           BITINIT -> if the signal has only a bit BITINIT="" otherwhise BITINIT="[BITNUMBER-1:0]"
                           SIGNAME -> It is substituted with signal name
        -- INSTANCE block_name
               PARAM = 
               IN = IN_string   
               OUT= OUT_string
           END_INSTANCE -> create an instance of block_name connecting input/output signals adding string, 
               for example:
                   INSTANCE BLOCK
                       PARAM=PARAM
                       IN=IN[0]
                       OUT = OUT_to_vote[i]
                   END_INSTANCE
               Generate:
                   cv32e40p_compressed_decoder #(FPU) compressed_decoder
                   (
                       .instr_i(instr_i[0]),
                       .instr_o(instr_o_to_vote[i]),
                       .is_compressed_o(is_compressed_o_to_vote[i]),
                       .illegal_instr_o(illegal_instr_o_to_vote[i])
                   );
        
        -- INSTANCE_FOREACH block_name inout
               instance_template
           END_INSTANCE  -> This command cycle on input or output of block and substitute
                       variable in instance_template string in order to create instance of some
                       block connected to input, output or both of block_name block.
                       Variable can be:
                           BITNUMBER -> number of bit of the signal to connect
                           INDEX -> index of cycle
                           SIGNAME -> name of the signal
           
        -- OR_UNROLL start end operation signame -> this command unroll a reduction operation in order
                           to have better representation in schematic during complation.
                           For example:
                               assign err_detected_o = OP_UNROLL 0 3 | err_detected ;
                           Generate:
                               assign err_detected_o =   err_detected[0] 
                                                       | err_detected[1] 
                                                       | err_detected[2];
        -- OP_FOREACH block_name inout operation expression -> apply an operation between each input
                       or output of block_name block. For example:
                           assign block_err_detected[m] = OP_FOREACH BLOCK OUT | SIGNAME_block_err[m] ;
                       Generate:
                           assign block_err_detected[m] =   instr_o_block_err[m]
                                                          | illegal_instr_o_block_err[m]
                                                          | is_compressed_o_block_err[m];
           
        """

        #print(sf.mod_obj_dict["BLOCK"].GetInputSigNamesList())
        fp = open(sf.filename,"r") 
        data_orig=fp.read()
        tab="        "
        data_orig=data_orig.replace("\t",tab)


        ####  Substitution of constant
        data = data_orig.replace("MODULE_NAME",module_name)
        data = data.replace("PARAM_NAME", param_name)
        # substitute all BLOCK_MODNAME with corrsipetive module name
        for mod_ID,mod_obj in zip(sf.mod_obj_dict.keys(), sf.mod_obj_dict.values()):
            data = data.replace(mod_ID+"_MODNAME", mod_obj.GetModuleNameNoPrefix())
            data = data.replace("SIG_NUM-"+mod_ID +"-OUT", str(len(mod_obj.GetOutputSigNamesList())-1))
            data = data.replace("SIG_NUM-"+mod_ID +"-IN", str(len(mod_obj.GetInputSigNamesList())-1))

        data_line = data.split("\n")

        data_elab=""
        lineno=0
        linemax=len(data_line)

        # Elaboration cycle
        while lineno < linemax:
            line=data_line[lineno]
            indent_int= GetStringIndent(line) 
            line_indent = 1
            if type(indent_int)== int and indent_int > 0:
                indent_string = " "*(indent_int-1)
                line_indent  = len(indent_string.split(sf.indent))
            line_strip = line.strip()
            line_strip_split = line_strip.split(" ")

            # Parameter declaration
            if "PARAMETER_DECLARATION" in line_strip:
                if len(line_strip_split) == 2:
                    # get the dictionary of info of corresponding block
                    block_obj = sf.mod_obj_dict[line_strip_split[1]]
                    data_elab += block_obj.GetParameterDeclaration(0)
                else:
                    print("ERROR! PARAMETER_DECLARATION at line %d need "
                            "the name of block to copy parameter" % lineno)
                    exit(-1)

            elif "DECLARATION_FOREACH" in line_strip:
                # DEyCLARATION_FOREACH BLOCK IN_OUT
                #    INOUT logic [2:0]BITINIT SIGNAME,
                # END_DECLARATION_FOREACH

                if len(line_strip_split) >= 3:
                    block_obj = sf.mod_obj_dict[line_strip_split[1]]
                    inout=line_strip_split[2]

                    if len(line_strip_split) > 4:
                        cmd2 = {line_strip_split[3]: line_strip_split[4:]}
                    
                    [command, lineno]= GetInnerCommand(data_line, lineno, "END_DECLARATION_FOREACH")
                    data_elab += GetDeclarationForeach(block_obj, inout, \
                            command, cmd2, lineno, line_indent*sf.indent)
                else:
                    print("ERROR! DECLARATION_FOREACH at line %d needs"
                        "block name and IN/OUT/IN_OUT option" % lineno)
                    print("LINE: %s" % line_strip_split)
                    exit(-1)

            elif "INSTANCE " in line_strip:
                # INSTANCE BLOCK BLOCK_MODNAME_triplicated
                #         PARAM=PARAM
                #         IN = IN [i]
                #         OUT = OUT _to_vote[i]
                # END_INSTANCE
                if len(line_strip_split) == 3:
                    block_obj = sf.mod_obj_dict[line_strip_split[1]]
                    instance_name = line_strip_split[2]
                    [command, lineno]= GetInnerCommand(data_line, lineno, "END_INSTANCE")
                    #iprint(json.dumps(block,indent=4))
                    data_elab += GetCmdInstance(block_obj,  command, instance_name ,lineno, line_indent)
                    lineno-=1
                else:
                    print("ERROR! INSTANCE at line %d needs block name and instance name" % lineno)
                    exit(-1)

            elif "INSTANCE_FOREACH" in line_strip:
                # INSTANCE_FOREACH BLOCK OUT
                #         // Voter for TOVOTE signal, triple voter if
                #         // CDEC_TOUT[INDEX] == 1
                #         cv32e40p_conf_voter
                #         #(
                #                 .L1(BITNUMBER),
                #                 .TOUT(CDEC_TOUT[INDEX])
                #         ) voter_SIGNAME_INDEX
                #         (
                #                 .to_vote_i( SIGNAME_to_vote ),
                #                 .voted_o( SIGNAME),
                #                 .block_err_o( SIGNAME_block_err),
                #                 .broken_block_i(is_broken_o),
                #                 .err_detected_o(err_detected[INDEX]),
                #                 .err_corrected_o(err_corrected[INDEX])
                #         );
                # END_INSTANCE_FOREACH
                if len(line_strip_split) == 3:
                    block_obj = sf.mod_obj_dict[line_strip_split[1]]
                    inout = line_strip_split[2]
                    [command, lineno]= GetInnerCommand(data_line, lineno, "END_INSTANCE_FOREACH")
                    data_elab += GetInstanceForeach(block_obj,  command, inout, lineno, indent_int*" ")
                    lineno -=1 
                else:
                    print("ERROR! INSTANCE_FOREACH at line %d needs block name and inout parameter" % lineno)
                    exit(-1)    

            elif "OP_UNROLL" in line_strip:
                # assign err_detected_o = OP_UNROLL 3 | err_detected ;
                cmd = line_strip.split("=")[1].strip()
                cmd_split = cmd.split(" ")
                if len(cmd_split) > 5:
                    start=cmd_split[1]
                    end=cmd_split[2]
                    op=cmd_split[3]
                    sig=cmd_split[4]
                    data_elab += GetOpUnroll(line_strip, start, end, op, sig, lineno, indent_int*" ")
                else:
                    print("ERROR! OP_UNROLL at line %d needs block name and instance name" % lineno)
                    exit(-1) 

            elif "OP_FOREACH" in line_strip:
                # assign err_detected_o = OP_UNROLL 3 | err_detected ;
                i=0
                while i< len(line_strip_split):
                    if line_strip_split[i] == "OP_FOREACH":
                        if i+4 < len(line_strip_split):
                            cmd = line_strip_split[i:i+5]

                            i+=4
                        else:
                            print("ERROR! OP_FOREACH at line %d, some arguments are missing '%s'" % (lineno,line_strip))
                            exit(-1)
                    i+=1

                block_obj = sf.mod_obj_dict[cmd[1]]
                inout=cmd[2]
                op=cmd[3]
                sig=cmd[4]
                data_elab += GetOpForeach(line_strip, block_obj, inout, op, sig, lineno, indent_int*" ")


            else:
                data_elab+=line + "\n"
                
            lineno+=1

        return data_elab

filename_template="/media/tesla/Storage/Data/Scrivania/AllProject/Fare/Tesi/Esecuzione_tesi/cv32e40p_ft_tests/FTGenerator/ft_template.sv"
filename_block="/media/tesla/Storage/Data/Scrivania/AllProject/Fare/Tesi/Esecuzione_tesi/cv32e40p/rtl/cv32e40p_prefetch_buffer.sv"

def testGetElaboratedTravulog(filename_template, filename_block):
    module_filename_dict =  {"BLOCK": filename_block}
    template_filename = filename_template
    package_filename = ""
    tv = travulog( template_filename, package_filename, {}, module_prefix="cv32e40p_")
    print(tv.GetElaboratedTravulog("ciccio","VFDJ"))

#testGetElaboratedTravulog(filename_template,filename_block)





