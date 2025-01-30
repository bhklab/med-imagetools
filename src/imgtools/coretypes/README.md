# Class Inheritance Diagram

```mermaid
classDiagram
    class Vector3D {
        +float x
        +float y
        +float z
        +__iter__() Iterator[float]
        +__getitem__(idx: int|str) float
    }

    class Coordinate3D {
        +float x
        +float y
        +float z
        +__add__(other: Coordinate3D|Size3D) Coordinate3D
        +__sub__(other: Coordinate3D|Size3D) Coordinate3D
        +__iter__() Iterator[float]
        +__getitem__(idx: int|str) float
    }

    class Spacing3D {
        +float x
        +float y
        +float z
        +__iter__() Iterator[float]
        +__getitem__(idx: int|str) float
    }

    class Size3D {
        +float width
        +float height
        +float depth
        +volume: float
        +__iter__() Iterator[float]
        +__getitem__(idx: int|str) float
    }

    class ImageGeometry {
        +Size3D size
        +Coordinate3D origin
        +Direction direction
        +Spacing3D spacing
    }

    class Direction {
        +Matrix3DFlat matrix
        +from_matrix(matrix: Matrix3D) Direction
        +to_matrix() list[list[float]]
        +normalize() Direction
        +is_normalized(tol: float) bool
    }

    %% Inheritance Relationships
    Coordinate3D --|> Vector3D
    Spacing3D --|> Vector3D
    Size3D --|> Vector3D

    %% Composition Relationships
    ImageGeometry --> Size3D
    ImageGeometry --> Coordinate3D
    ImageGeometry --> Direction
    ImageGeometry --> Spacing3D
```

## Explanation

- **Inheritance (`--|>`)**
  - `Coordinate3D`, `Spacing`, and `Size3D` inherit from `Vector3D`.
- **Composition (`-->`)**
  - `ImageGeometry` **contains** `Size3D`, `Coordinate3D`, `Direction`, and `Spacing3D`.
