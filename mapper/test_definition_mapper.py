import logging

from models.test_definition import TestDefinition
from models.variable import Variable
from parser.excel_test_definition_row import ExcelTestDefinitionRow
from parser.variable_order_parser import VariableOrderParser
from parser.variable_value_parser import VariableValueParser

logger = logging.getLogger(__name__)


class TestDefinitionMapper:

    def __init__(self):
        self.variable_value_parser = VariableValueParser()
        self.variable_order_parser = VariableOrderParser()

    def map(self, row: ExcelTestDefinitionRow) -> TestDefinition:

        # ---------------------------------------------------------------- #
        # Headers                                                            #
        # ---------------------------------------------------------------- #
        headers_dict: dict[str, str] = {}
        if row.headers:
            for line in row.headers.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    headers_dict[key.strip()] = val.strip()

        # ---------------------------------------------------------------- #
        # Strategy                                                           #
        # variable_strategy column may contain "random/sequential" in       #
        # legacy sheets — normalise to a single keyword.                    #
        # ---------------------------------------------------------------- #
        strategy_raw = (row.variable_strategy or "").lower()
        if "random" in strategy_raw:
            strategy = "random"
        elif "sequential" in strategy_raw:
            strategy = "sequential"
        else:
            strategy = "sequential"

        # ---------------------------------------------------------------- #
        # Variables                                                          #
        #                                                                    #
        # variable_values: multi-value  e.g. "v1:{a,b,c}, v2:{x,y}"        #
        # fixed_variables: single-value e.g. "v1:abc, v2:123"              #
        #                                                                    #
        # fixed_variables are treated as single-element lists so they       #
        # participate in combination generation normally.                    #
        # ---------------------------------------------------------------- #
        variables: list[Variable] = []

        if row.variable_values:
            variables = self.variable_value_parser.parse(row.variable_values)

        if row.fixed_variables:
            fixed = self.variable_value_parser.parse(row.fixed_variables)
            existing_names = {v.name for v in variables}
            for v in fixed:
                if v.name not in existing_names:
                    variables.append(v)
                else:
                    # fixed value overrides the multi-value entry
                    for existing in variables:
                        if existing.name == v.name:
                            existing.values = v.values
                            break

        # ---------------------------------------------------------------- #
        # Variable ordering                                                  #
        # variable_order is a comma-separated list of variable names that   #
        # sets the iteration order for sequential strategy.                  #
        # ---------------------------------------------------------------- #
        if row.variable_order and variables:
            # Only treat as an ordering list when it looks like variable names,
            # not when it's the strategy hint ("random/sequential").
            raw_order = row.variable_order.strip()
            if raw_order.lower() not in ("random/sequential", "sequential", "random"):
                ordered_names = self.variable_order_parser.parse(raw_order)
                if ordered_names:
                    var_map = {v.name: v for v in variables}
                    ordered_variables: list[Variable] = []
                    for name in ordered_names:
                        if name in var_map:
                            ordered_variables.append(var_map[name])
                        else:
                            logger.warning(
                                "Variable '%s' in variable_order not found in variable_values — skipping.",
                                name,
                            )
                    # Append any variables not mentioned in the order list
                    for v in variables:
                        if v.name not in set(ordered_names):
                            ordered_variables.append(v)
                    variables = ordered_variables

        return TestDefinition(
            url=row.url,
            method=row.method.upper() if row.method else "GET",
            strategy=strategy,
            headers=headers_dict,
            request_template=row.request_template or "",
            variables=variables,
            concurrency=int(float(row.concurrency)) if row.concurrency is not None else 1,
            enabled=row.enabled.lower() == "enable" if row.enabled else False,
            response_structure=row.response_structure or None,
            ramp_up_seconds=int(float(row.ramp_up_seconds)) if row.ramp_up_seconds is not None else 0,
        )
