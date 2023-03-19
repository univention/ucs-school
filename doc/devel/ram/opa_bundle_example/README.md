# OPA bundle example

This repository contains an example of an OPA bundle.

## Bundle structure

```text
.
├── conditions.rego
├── mapping
│   └── data.json
├── test_conditions.rego
├── test_utils.rego
└── utils.rego
```

## Testing

To test the bundle, run the following command:

```bash
opa test -v .
```

## Run interactively

To run the bundle interactively, run the following command:

```bash
opa run .
```

Then you can copy examples from the tests, for example:

```rego
package univention.conditions
cap_condition(
        "targetHasRole",
        null,
        {
                "name": "student1",
                "school": "school1",
                "roles": ["ucsschool.school1.student"],
        },
        null,
        null,
        {"role": "ucsschool.school1.student"},
)
```
