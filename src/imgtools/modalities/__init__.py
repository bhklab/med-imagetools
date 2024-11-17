"""
@property
def referenced_series_uid(self) -> str:
    uid: str = self.dataset.ReferencedSeriesSequence[0].SeriesInstanceUID
    return uid

@property
def referenced_instance_uids(self) -> List[str]:
    return [
        x.ReferencedSOPInstanceUID
        for x in self.dataset.ReferencedSeriesSequence[0].ReferencedInstanceSequence
    ]

"""
