from par.models import AlertRule


def make_alert(**kwargs) -> AlertRule:
    defaults = dict(
        name="TestAlert",
        expr='up{job="test"} == 0',
        for_duration="5m",
        labels={"severity": "warning", "owner": "sre"},
        annotations={"summary": "x", "description": "x", "runbook_url": "x", "dashboard_url": "x"},
        group_name="test_group",
        file_path="test.yaml",
        line=1,
        suppressed=set(),
    )
    defaults.update(kwargs)
    return AlertRule(**defaults)
