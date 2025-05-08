# `nnUNetPipeline`: Structured DICOM-to-NIfTI Conversion for Deep Learning

## TL;DR  
`nnUNetPipeline` is a variation of `AutoPipeline` that simplifies the messy reality of clinical imaging data by converting raw DICOM files into the [nnUNet](https://github.com/MIC-DKFZ/nnUNet) standard.  

It's fast, reproducible, and designed for segmentation workflows using CT/MR with `RTSTRUCT` or `SEG`.

---

## Why `nnUNetPipeline`?

`nnUNet` is the standard for training deep automated segmentation models on medical images.

`nnUNetPipeline`:

- Crawls and indexes DICOM files
- Links scans to associated segmentations
- Applies optional transforms (e.g., resample, window/level)
- Matches ROI labels to your standard keys
- Outputs clean NIfTI files for training with `nnUNet`

---

## Comparison to `AutoPipeline`

| Feature                     | `nnUNetPipeline`                                   | `Autopipeline`                                         |
|-----------------------------|----------------------------------------------------|--------------------------------------------------------|
| **Primary Use Case**         | Converts clinical DICOMs into nnUNet-ready        | General-purpose medical image processing               |
| **Modalities**               | Specific pairs of CT/MR with `RTSTRUCT` or `SEG`  | Flexible, supports any modality list                   |
| **ROI Matching**             | Requires `roi_match_map` for nnUNet compatibility | Optional, with more flexibility for handling ROIs      |
| **Mask Saving Strategy**     | Uses `MaskSavingStrategy` (e.g., `sparse_mask`)    | Saves each ROI as a separate mask file                |
| **ROI Strategy**             | `ROIMatchStrategy.MERGE` for overlaps              | Default is `ROIMatchStrategy.SEPARATE`                |

---

## Key Features

- ✅ Supports modality pairs: `["CT", "SEG"]`, `["MR", "SEG"]`, `["CT", "RTSTRUCT"]`, `["MR", "RTSTRUCT"]`
- ✅ Supports different `mask_saving_strategy` options (`"label_image"`, `"sparse_mask"`, `"region_mask"`)
- ✅ Matches ROIs via regex patterns (`"GTV": ["gtv", "Gross.*Volume"]`)
- ✅ Provides `nnUNet`-specific scripts for preprocessing and training

---

## Mask Saving Options

When converting segmentations (e.g., from `RTSTRUCT` or `SEG`) into NIfTI masks for training, you have multiple options depending on how you want to handle overlapping regions and label representation.

### `label_image`

- **Single-channel label image**  
- Each voxel contains an integer label corresponding to a single region.
- **Limitations**:
  - Does **not** allow overlapping ROIs.
  - Each voxel can belong to **only one** region.
- Use this when you're certain there are no overlaps, and you want compatibility with standard segmentation workflows.

---

### `sparse_mask`

- **Single-channel label image**  
- Each voxel contains an integer label corresponding to a single region.
- **Overlapping regions are allowed** in the input, but only one label is assigned per voxel in the output.
- When overlaps occur, the label from the **last matching region (highest index)** is assigned, and earlier labels are overwritten.
- User can decide the order when passing in ROI map.
- **Lossy** if regions overlap, since only one region label is retained per voxel and all others are discarded.

---

### `region_mask` (Recommended for nnU-Net)

- **Bitmask encoding of overlapping ROIs**  
- Inspired by nnU-Net’s [region-based training](https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/region_based_training.md).
- Every **unique combination** of ROIs gets its own integer label — preserving overlap information **without loss**.
- Enables multi-class region training with full overlap preservation.

#### How It Works

Internally, this uses a bitmask approach. Each voxel stores a value representing a combination of active ROI channels (up to 32 ROIs supported).

Imagine you have three regions of interest (ROIs):

- `GTV` assigned to **bit 0** → value `2^0 = 1`
- `Cord` assigned to **bit 1** → value `2^1 = 2`
- `Parotid_L` assigned to **bit 2** → value `2^2 = 4`

Each voxel in the mask encodes a combination of these ROIs using **bitwise addition**.

| Voxel Location | Present ROIs           | Bitmask Calculation                 | Encoded Value |
|----------------|------------------------|-------------------------------------|---------------|
| (10, 30, 40)   | GTV                    | `2^0`                               | 1             |
| (12, 30, 40)   | Cord                   | `2^1`                               | 2             |
| (15, 30, 40)   | Parotid_L              | `2^2`                               | 4             |
| (17, 30, 40)   | GTV + Parotid_L        | `2^0 + 2^2 = 2^0 + 2^2 = 1 + 4`     | 5             |
| (20, 30, 40)   | GTV + Cord + Parotid_L | `2^0 + 2^1 + 2^2 = 1 + 2 + 4`       | 7             |

---

### Choosing the Right Strategy

| Option         | Overlaps | Lossless |
|----------------|----------|----------|
| `label_image`  | ❌       | ✅       | 
| `sparse_mask`  | ✅       | ❌       |
| `region_mask`  | ✅       | ✅       |

## Example CLI Usage

```bash
imgtools nnunet-pipeline \
    --modalities CT,RTSTRUCT \
    --roi-match-yaml roi_patterns.yaml \
    --mask-saving-strategy region_mask \
    /data/dicoms/ \
    /data/nnunet_ready/
```