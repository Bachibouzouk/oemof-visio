import subprocess
import oemof.solph as solph
import pandas as pd

z_version = 1
OEMOF_0_5_X_RELEASE = False
OEMOF_0_5_1_RELEASE = False
if solph.__version__[:3] == "0.4":
    from oemof.solph import (
        Source,
        Sink,
        Transformer
    )
    from oemof.solph.plumbing import _Sequence as sequence

    SOLPH_INVESTMENT = "solph.options.Investment"
    SOLPH_NON_CONVEX = "solph.options.NonConvex"
    INVESTMENT_DEFAULT = solph.options.Investment().__dict__
    NON_CONVEX_DEFAULT = solph.options.NonConvex().__dict__


else:
    OEMOF_0_5_X_RELEASE = True
    from oemof.solph._plumbing import _Sequence as sequence
    from oemof.solph.components import (
        Source,
        Sink,
    )
    if solph.__version__[:3] == "0.5" and int(solph.__version__.split(".")[2]) >= z_version:
        OEMOF_0_5_1_RELEASE = True
        from oemof.solph.components import Converter as Transformer
    else:
        from oemof.solph.components import Transformer

    SOLPH_INVESTMENT = "solph.Investment"
    SOLPH_NON_CONVEX = "solph.NonConvex"
    INVESTMENT_DEFAULT = solph.Investment().__dict__
    NON_CONVEX_DEFAULT = solph.NonConvex().__dict__
# coefficient value if provided
FLOW_DEFAULT = solph.Flow().__dict__
flow_default = FLOW_DEFAULT




def is_bus_flow_dict(d):
    answer = False
    if isinstance(d, dict):
        answer = 0
        for k, v in d.items():
            if isinstance(k, solph.Bus) and isinstance(v, solph.Flow):
                pass
            else:
                answer = answer + 1
        answer = answer == 0
    return answer


def parse_investment(inv):
    investment_arguments = []
    for p, pval in inv.__dict__.items():
        if p in INVESTMENT_DEFAULT:
            if INVESTMENT_DEFAULT[p] != pval:
                investment_arguments.append(f"{p}={pval}")
        else:
            investment_arguments.append(f"{p}={pval}")
    return f"{SOLPH_INVESTMENT}({', '.join(investment_arguments)})"


def parse_sequence(v):

    if len(v) == 0:
        answer = f"{v[0]}"
    else:
        answer = f"[{','.join([str(el) for el in v])}]"

    if answer == "None" or answer == "['None']" or answer == "[None]":
        answer = v
    return answer


def parse_class_dict(adict, default={}):
    instance_arguments = []
    for p, pval in adict.items():
        if isinstance(pval, sequence):
            pval = parse_sequence(pval)
        if p in default:
            if default[p] != pval:
                instance_arguments.append(f"{p}: {pval}")
        else:
            instance_arguments.append(f"{p}: {pval}")
    answer = f"{{{', '.join(instance_arguments)}}}"
    if answer == "{}":
        answer = adict
    return answer


def parse_nonconvex(nonconvex):
    nonconvex_arguments = []
    for p, pval in nonconvex.__dict__.items():
        if isinstance(pval, sequence):
            pval = parse_sequence(pval)
        if isinstance(pval, dict):
            pval = parse_class_dict(
                pval, default=NON_CONVEX_DEFAULT["positive_gradient"]
            )
        if p in NON_CONVEX_DEFAULT:
            if NON_CONVEX_DEFAULT[p] != pval:
                nonconvex_arguments.append(f"{p}={pval}")
        else:
            if p[0] != "_":
                nonconvex_arguments.append(f"{p}={pval}")

    return f"{SOLPH_NON_CONVEX}({', '.join(nonconvex_arguments)})"


def parse_flow(flow):
    flow_arguments = []
    for p, pval in flow.__dict__.items():

        if p in FLOW_DEFAULT:
            if isinstance(pval, solph.plumbing._Sequence):
                try:
                    pval = parse_sequence(pval)
                except:
                    print(p)
                    print(pval)

            if FLOW_DEFAULT[p] != pval:
                if p == "investment":
                    flow_arguments.append(f"{p}={parse_investment(pval)}")
                elif p == "nonconvex":
                    flow_arguments.append(f"{p}={parse_nonconvex(pval)}")
                else:
                    flow_arguments.append(f"{p}={pval}")
        else:
            if p[0] != "_":
                flow_arguments.append(f"{p}={pval}")
    return f"solph.Flow({', '.join(flow_arguments)})"



def parse_bus_flow_dict(d):
    bus_flow_pairs = []
    for bus, flow in d.items():
        bus_flow_pairs.append(f"{bus.label}: {parse_flow(flow)}")
    return bus_flow_pairs


class ESCodeRenderer:
    def __init__(self, energy_system):
        self.energy_system = energy_system
        self.es_variable_name = "energy_system"
        self.busses = [n for n in self.energy_system.nodes if isinstance(n, solph.Bus)]
        self.sources = [
            n for n in self.energy_system.nodes if isinstance(n, Source)
        ]
        self.sinks = [n for n in self.energy_system.nodes if isinstance(n, Sink)]
        self.transformers = [
            n for n in self.energy_system.nodes if isinstance(n, Transformer)
        ]
        self.storages = [
            n
            for n in self.energy_system.nodes
            if isinstance(n, solph.components.GenericStorage)
        ]
        self.chps = [
            n
            for n in self.energy_system.nodes
            if isinstance(n, solph.components.GenericCHP)
        ]
        self.extractions_turbines = [
            n
            for n in self.energy_system.nodes
            if isinstance(n, solph.components.ExtractionTurbineCHP)
        ]
        self.offset_transformers = [
            n
            for n in self.energy_system.nodes
            if isinstance(n, solph.components.OffsetTransformer)
        ]

    def print(self, fname=None):
        answer = (
                self.print_import_statements()
                + self.print_timeindex()
                + self.print_es_definition()
                + self.print_busses()
                + self.print_transformers()
                + self.print_chps()
                + self.print_extraction_turbines()
                + self.print_offet_transformers()
                + self.print_storages()
                + self.print_sources()
                + self.print_sinks()
                + self.print_model_definition()
        )
        if fname is None:
            for l in answer:
                print(l)
        else:
            with open(fname,"w") as fp:
                fp.writelines(f"{l}\n" for l in answer)
            subprocess.run(["black", fname])
    def print_import_statements(self):
        answer = [""]
        answer.append("import oemof.solph as solph")
        answer.append("from pandas import DatetimeIndex")
        answer.append("")
        return answer

    def print_timeindex(self):
        return ["", f"tindex = {self.energy_system.timeindex.__str__()}", ""]

    def print_es_definition(self):
        return ["", f"{self.es_variable_name} = solph.EnergySystem(timeindex=tindex)", ""]

    def print_model_definition(self):
        answer = [""]
        answer.append(f"om = solph.Model({self.es_variable_name})")
        answer.append('om.write("rendered_lp_file.lp", io_options={"symbolic_solver_labels": True})')
        answer.append('om.solve(solver="cbc", solve_kwargs={"tee": True})')
        return answer

    def print_busses(self):
        answer = [""]
        for bus in self.busses:
            answer.append(f"{bus.label} = solph.Bus(label='{bus.label}')")
            answer.append(f"{self.es_variable_name}.add({bus.label})")
        answer.append("")
        return answer

    def print_transformers(self):
        answer = []
        for i, t in enumerate(self.transformers):
            answer.append("")
            answer = answer + self.print_single_transformer(t, variable_name=f"t{i+1}")
            answer.append("")
        return answer

    def print_single_transformer(self, t, variable_name="t"):
        all_args = {}
        all_args["label"] = f"'{t.label}'"
        input_params = parse_bus_flow_dict(t.inputs)

        all_args["inputs"] = "{" + ", ".join(input_params) + "}"

        output_params = parse_bus_flow_dict(t.outputs)

        all_args["outputs"] = "{" + ", ".join(output_params) + "}"

        conv_factors = []
        for k, v in t.conversion_factors.items():
            parse_sequence(v)
            conv_factors.append(f"{k}: {v}")
        all_args["conversion_factors"] = "{" + ", ".join(conv_factors) + "}"

        answer = []
        if OEMOF_0_5_1_RELEASE is True:
            answer.append(f"{variable_name} = solph.components.Converter(")
        elif OEMOF_0_5_X_RELEASE is True:
            answer.append(f"{variable_name} = solph.components.Source(")
        else:
            answer.append(f"{variable_name} = solph.Transformer(")
        for a, v in all_args.items():
            answer.append("  " + f"{a}={v},")
        answer.append(")")
        answer.append("")
        answer.append(f"{self.es_variable_name}.add({variable_name})")
        answer.append("")

        return answer

    def print_chps(self):
        answer = []
        for i, t in enumerate(self.chps):
            answer.append("")
            answer = answer + self.print_single_chp(t, variable_name=f"chp{i+1}")
            answer.append("")
        return answer

    def print_single_chp(self, t, variable_name="t"):
        all_args = {}
        all_args["label"] = f"'{t.label}'"

        for k, v in t.__dict__.items():
            if is_bus_flow_dict(v) is True:
                dict_arguments = parse_bus_flow_dict(v)
                all_args[k] = "{" + ", ".join(dict_arguments) + "}"
            elif k[0] != "_":
                all_args[k] = v

        answer = []
        answer.append(f"{variable_name} = solph.components.GenericCHP(")
        for a, v in all_args.items():
            answer.append("  " + f"{a}={v},")
        answer.append(")")
        answer.append("")
        answer.append(f"{self.es_variable_name}.add({variable_name})")
        answer.append("")

        return answer

    def print_sources(self):
        answer = []
        for i, s in enumerate(self.sources):
            answer.append("")
            answer = answer + self.print_single_source(s, variable_name=f"source{i+1}")
            answer.append("")
        return answer

    def print_single_source(self, s, variable_name="s"):
        all_args = {}
        all_args["label"] = f"'{s.label}'"

        output_params = parse_bus_flow_dict(s.outputs)
        all_args["outputs"] = "{" + ", ".join(output_params) + "}"

        answer = []
        if OEMOF_0_5_X_RELEASE is True:
            answer.append(f"{variable_name} = solph.components.Source(")
        else:
            answer.append(f"{variable_name} = solph.Source(")
        for a, v in all_args.items():
            answer.append("  " + f"{a}={v},")
        answer.append(")")
        answer.append("")
        answer.append(f"{self.es_variable_name}.add({variable_name})")
        answer.append("")

        return answer

    def print_sinks(self):
        answer = []
        for i, s in enumerate(self.sinks):
            answer.append("")
            answer = answer + self.print_single_sink(s, variable_name=f"sink{i+1}")
            answer.append("")
        return answer

    def print_single_sink(self, s, variable_name="s"):
        all_args = {}
        all_args["label"] = f"'{s.label}'"
        input_params = parse_bus_flow_dict(s.inputs)
        all_args["inputs"] = "{" + ", ".join(input_params) + "}"

        answer = []
        if OEMOF_0_5_X_RELEASE is True:
            answer.append(f"{variable_name} = solph.components.Sink(")
        else:
            answer.append(f"{variable_name} = solph.Sink(")
        for a, v in all_args.items():
            answer.append("  " + f"{a}={v},")
        answer.append(")")
        answer.append("")
        answer.append(f"{self.es_variable_name}.add({variable_name})")
        answer.append("")

        return answer

    def print_storages(self):
        answer = []
        for i, s in enumerate(self.storages):
            answer.append("")
            answer = answer + self.print_single_storage(
                s, variable_name=f"storage{i+1}"
            )
            answer.append("")
        return answer

    def print_single_storage(self, s, variable_name="s"):
        return self.print_custom(
            s, variable_name, component_name="solph.components.GenericStorage"
        )

    def print_extraction_turbines(self):
        answer = []
        for i, s in enumerate(self.extractions_turbines):
            answer.append("")
            answer = answer + self.print_single_extraction_turbine(
                s, variable_name=f"extr_turb{i+1}"
            )
            answer.append("")
        return answer

    def print_single_extraction_turbine(self, s, variable_name="s"):
        return self.print_custom(
            s, variable_name, component_name="solph.components.ExtractionTurbineCHP"
        )

    def print_offet_transformers(self):
        answer = []
        for i, t in enumerate(self.offset_transformers):
            answer.append("")
            answer = answer + self.print_single_offet_transformer(
                t, variable_name=f"offset_t{i + 1}"
            )
            answer.append("")
        return answer

    def print_single_offet_transformer(self, t, variable_name="s"):
        return self.print_custom(
            t, variable_name, component_name="solph.components.OffsetTransformer"
        )

    def print_custom(self, s, variable_name="s", component_name="solph.components"):
        all_args = {}
        all_args["label"] = f"'{s.label}'"
        input_params = parse_bus_flow_dict(s.inputs)
        all_args["inputs"] = "{" + ", ".join(input_params) + "}"

        output_params = parse_bus_flow_dict(s.outputs)
        all_args["outputs"] = "{" + ", ".join(output_params) + "}"

        for k, v in s.__dict__.items():
            if is_bus_flow_dict(v) is True:
                dict_arguments = parse_bus_flow_dict(v)
                all_args[k] = "{" + ", ".join(dict_arguments) + "}"
            elif k[0] != "_":
                if isinstance(v, sequence):
                    v = parse_sequence(v)
                all_args[k] = v

        answer = []
        answer.append(f"{variable_name} = {component_name}(")
        for a, v in all_args.items():
            answer.append("  " + f"{a}={v},")
        answer.append(")")
        answer.append("")
        answer.append(f"{self.es_variable_name}.add({variable_name})")
        answer.append("")

        return answer