from dataclasses import dataclass
from typing import List
from .transforms import BaseTransform, SpatialTransform, IntensityTransform
from SimpleITK import Image
from copy import deepcopy
@dataclass
class Transformer:
    transforms: List[BaseTransform]

    def __call__(self, images: List[Image]):
        new_images = []
        ref_image = None
        for n, image in enumerate(images):
            new_image = deepcopy(image)
            for transform in self.transforms:
                # apply spatial transforms to all images
                if isinstance(transform, SpatialTransform):
                    new_image = transform(new_image, ref=ref_image)
                # only apply intensity transforms to the first image
                elif isinstance(transform, IntensityTransform) and n == 0: 
                    new_image = transform(new_image)
            new_images.append(new_image)
            
            # set reference image for future spatial transforms
            if n == 0:
                ref_image = new_image