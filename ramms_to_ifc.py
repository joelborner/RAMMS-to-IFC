import ifcopenshell
from ifcopenshell import guid
import numpy as np
from scipy.spatial import ConvexHull
import struct

# Required parameters to generate IFC file               |  Data from RAMMS
# ------------------------------------------------------------------------------------------------------
# Local coordinate system (point and 2 vectors)          |  Rock center of mass x,y,z and Quaternion
# Rock vertices (point cloud) in local coordinates       |  .pts file
# List of vertex indices connected to triangular faces   |  convex hull algorithm (directly from RAMMS?)
# Additional optional property fields                    |  current velocity, energy, jump height etc.


def read_pts_file(file_path):
    with open(file_path, 'r') as f:
        points = np.loadtxt(f)
    return points


def get_convex_hull_faces(points):
    # function to get a list of indices that connect the corresponding vertices to triangular faces
    hull = ConvexHull(points)
    faces = hull.simplices
    return faces


def quaternion_to_rotated_vectors(w, x, y, z):
    # Calculate the rotation matrix from the quaternion
    rotation_matrix = np.array([[1 - 2 * y * y - 2 * z * z, 2 * x * y - 2 * w * z, 2 * x * z + 2 * w * y],
                                [2 * x * y + 2 * w * z, 1 - 2 * x * x - 2 * z * z, 2 * y * z - 2 * w * x],
                                [2 * x * z - 2 * w * y, 2 * y * z + 2 * w * x, 1 - 2 * x * x - 2 * y * y]])

    # Transform the unit vectors along the x, y, and z axes by the rotation matrix
    x_axis = tuple(float(i) for i in rotation_matrix @ np.array([1, 0, 0]))
    z_axis = tuple(float(i) for i in rotation_matrix @ np.array([0, 0, 1]))

    # Return the rotated vectors
    return x_axis, z_axis


def read_rts(filename):
    trajectory_name = filename.split("/")[-1].split(".rts")[0]
    # Open the file and read all lines into a list
    with open(filename, 'rb') as file:
        file_content = file.read()
        num_doubles = len(file_content) // 8
        doubles = struct.unpack("d" * num_doubles, file_content)
    rock_mass = doubles[0]
    cut_list = doubles[4:]
    return rock_mass, [cut_list[i:i+26] for i in range(0, len(cut_list), 26)]


def ramms_to_ifc(scenario_name, trajectory_data, gap_length, pts_path, color_option):
    points = read_pts_file(pts_path)
    faces = get_convex_hull_faces(points)
    # convert 2D numpy arrays to tuples of tuples (required by ifcopenshell)
    points_ifc = tuple(map(tuple, points.tolist()))
    faces_ifc = tuple(map(tuple, faces.tolist()))
    faces = tuple(tuple(val+1 for val in inner_t) for inner_t in faces_ifc)  # vertex indices for ifc start at 1 and not 0
    e_max = 0
    h_max = 0
    if color_option > 1:
        for t in trajectory_data:
            for data in t[2]:
                if color_option == 2 and data[15] > e_max:
                    e_max = float(data[15])
                elif data[3]-data[18] > h_max:
                    h_max = float(data[3]-data[15])

    # Create a new IFC file
    file = ifcopenshell.file()
    # create global coordinate system
    direction_1 = file.create_entity("IfcDirection", (0.0, 1.0))
    direction_2 = file.create_entity("IfcDirection", (1.0, 0.0, 0.0))
    direction_3 = file.create_entity("IfcDirection", (0.0, 0.0, 1.0))
    cartesian_point = file.create_entity("IfcCartesianPoint", (0.0, 0.0, 0.0))
    axis_placement = file.create_entity("IfcAxis2Placement3D", cartesian_point, direction_3, direction_2)
    geometric_context = file.create_entity("IfcGeometricRepresentationContext", ContextType="Model", CoordinateSpaceDimension=3, Precision=0.00001, WorldCoordinateSystem=axis_placement, TrueNorth=direction_1)
    # define general project information and units
    project_info = {
        "GlobalId": ifcopenshell.guid.new(),
        "Name": "Rockfall Trajectories",
        "Description": "Exported from RAMMS::Rockfall",
        "UnitsInContext": file.create_entity("IfcUnitAssignment",
                                                  Units=[file.create_entity("IfcSIUnit", UnitType='LENGTHUNIT', Prefix=None, Name='METRE'),
                                                         file.create_entity("IfcSIUnit", UnitType='AREAUNIT', Prefix=None, Name='SQUARE_METRE'),
                                                         file.create_entity("IfcSIUnit", UnitType='VOLUMEUNIT', Prefix=None, Name='CUBIC_METRE')]),
        "RepresentationContexts": [geometric_context]
    }
    # Create the project, site and building
    project = file.create_entity("IfcProject", **project_info)
    site = file.create_entity("IfcSite", GlobalId=ifcopenshell.guid.new(), Name="Antoniberg")
    file.create_entity("IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), RelatingObject=project, RelatedObjects=[site])
    release = file.create_entity("IfcBuilding", GlobalId=ifcopenshell.guid.new(), Name='RAMMS Simulation', ObjectPlacement=axis_placement)
    file.create_entity("IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), RelatingObject=site, RelatedObjects=[release])
    point_list = file.create_entity("IfcCartesianPointList3D", points_ifc)
    if color_option == 1:
        col_rgb = file.create_entity("IfcColourRgb", Red=0.5, Green=0.5, Blue=0.5)
        surface_style_rendering = file.create_entity("IfcSurfaceStyleRendering", SurfaceColour=col_rgb,
                                                     Transparency=0, ReflectanceMethod="FLAT")
        surface_style = file.create_entity("IfcSurfaceStyle", Name="RockSurfStyle", Side="BOTH",
                                           Styles=[surface_style_rendering])
        style_assignment = file.create_entity("IfcPresentationStyleAssignment", [surface_style])
        # Create geometry of a single rock according to .pts file and convex hull, assign rendering style to it
        face_list = file.create_entity("IfcTriangulatedFaceSet", Coordinates=point_list, CoordIndex=faces,
                                       Closed=True)
        shape_representation = file.create_entity("IfcShapeRepresentation", ContextOfItems=geometric_context,
                                                  RepresentationIdentifier="Body",
                                                  RepresentationType="Tessellation", Items=[face_list])
        product_definition_shape = file.create_entity("IfcProductDefinitionShape",
                                                      Representations=[shape_representation])
        styled_item = file.create_entity("IfcStyledItem", Item=face_list, Styles=[style_assignment])
    # go through all trajectories, each trajectory is grouped in a IfcBuildingStorey entity
    for a in range(len(trajectory_data)):
        trajectory = file.create_entity("IfcBuildingStorey", GlobalId=ifcopenshell.guid.new(), Name=trajectory_data[a][1], ObjectPlacement=axis_placement)
        file.create_entity("IfcRelAggregates", GlobalId=ifcopenshell.guid.new(), RelatingObject=release, RelatedObjects=[trajectory])
        rock_name_prop = file.create_entity("IfcPropertySingleValue", "Rock Name",
                                            NominalValue=file.create_entity("IfcText", pts_path.split("/")[-1]))
        rock_mass_prop = file.create_entity("IfcPropertySingleValue", "Rock Mass [kg]",
                                            NominalValue=file.create_entity("IfcReal", float(trajectory_data[a][0])))
        last_pos = (0, 0, 0)
        # go through every dump step of a specific trajectory, create local coordinate system and place rock
        for i in range(len(trajectory_data[a][2])):
            # calculate the distance to the last rendered rock and only draws a new rock if the distance is bigger than the defined gap length
            pos = (float(trajectory_data[a][2][i][1]), float(trajectory_data[a][2][i][2]), float(trajectory_data[a][2][i][3]))
            distance = np.sqrt((pos[0]-last_pos[0]) ** 2 + (pos[1]-last_pos[1]) ** 2 + (pos[2]-last_pos[2]) ** 2)
            if distance > gap_length or i == len(trajectory_data[a][2]) - 1:
                # create list of properties for every rendered dump step (kinetic energy, jump height, velocity, etc.)
                rock_energy = file.create_entity("IfcPropertySingleValue", "Kinetic Energy [kJ]", NominalValue=file.create_entity("IfcReal", float(trajectory_data[a][2][i][15] / 1000)))
                rock_jump_height = file.create_entity("IfcPropertySingleValue", "Jump Height [m]", NominalValue=file.create_entity("IfcReal", float(trajectory_data[a][2][i][3] - trajectory_data[a][2][i][18])))
                rock_velocity = file.create_entity("IfcPropertySingleValue", "Velocity [m/s]", NominalValue=file.create_entity("IfcReal", float(np.sqrt(trajectory_data[a][2][i][8] ** 2 + trajectory_data[a][2][i][9] ** 2 + trajectory_data[a][2][i][10] ** 2))))
                rock_properties = file.create_entity("IfcPropertySet", GlobalId=ifcopenshell.guid.new(), Name="Rockfall Attributes", HasProperties=[rock_energy, rock_jump_height, rock_velocity, rock_name_prop, rock_mass_prop])
                # Define rendering style including color gradient
                if color_option > 1:
                    if color_option == 2:
                        color = (1 - float(trajectory_data[a][2][i][15]) / e_max) ** 2
                    else:
                        color = (1 - float(trajectory_data[a][2][i][3] - trajectory_data[a][2][i][18]) / h_max) ** 2
                    col_rgb = file.create_entity("IfcColourRgb", Red=1-color, Green=0, Blue=color)
                    surface_style_rendering = file.create_entity("IfcSurfaceStyleRendering", SurfaceColour=col_rgb,
                                                                 Transparency=0, ReflectanceMethod="FLAT")
                    surface_style = file.create_entity("IfcSurfaceStyle", Name="RockSurfStyle", Side="BOTH",
                                                       Styles=[surface_style_rendering])
                    style_assignment = file.create_entity("IfcPresentationStyleAssignment", [surface_style])
                    # Create geometry of a single rock according to .pts file and convex hull, assign rendering style to it
                    face_list = file.create_entity("IfcTriangulatedFaceSet", Coordinates=point_list, CoordIndex=faces,
                                                   Closed=True)
                    shape_representation = file.create_entity("IfcShapeRepresentation", ContextOfItems=geometric_context,
                                                              RepresentationIdentifier="Body",
                                                              RepresentationType="Tessellation", Items=[face_list])
                    product_definition_shape = file.create_entity("IfcProductDefinitionShape",
                                                                  Representations=[shape_representation])
                styled_item = file.create_entity("IfcStyledItem", Item=face_list, Styles=[style_assignment])
                # define local coordinate system according to center of mass of the rock and quaternion
                rock_center_of_mass = file.create_entity("IfcCartesianPoint", (pos[0], pos[1], pos[2]))
                x_rotation, z_rotation = quaternion_to_rotated_vectors(float(trajectory_data[a][2][i][4]), float(trajectory_data[a][2][i][5]), float(trajectory_data[a][2][i][6]), float(trajectory_data[a][2][i][7]))
                rot_direction_2 = file.create_entity("IfcDirection", x_rotation)
                rot_direction_3 = file.create_entity("IfcDirection", z_rotation)
                rock_axis = file.create_entity("IfcAxis2Placement3D", rock_center_of_mass, rot_direction_3, rot_direction_2)
                # place the rock in local coordinate system and create entity
                rock_placement = file.create_entity("IfcLocalPlacement", RelativePlacement=rock_axis)
                rock_position = file.create_entity("IfcBuildingElementProxy", GlobalId=ifcopenshell.guid.new(), Name="t = " + str(round(trajectory_data[a][2][i][0], 3)) + " s", ObjectPlacement=rock_placement, Representation=product_definition_shape)
                contained_spatial_structure = file.create_entity("IfcRelContainedInSpatialStructure", GlobalId=ifcopenshell.guid.new(), RelatingStructure=trajectory, RelatedElements=[rock_position])
                file.create_entity("IfcRelDefinesByProperties", GlobalId=ifcopenshell.guid.new(), RelatedObjects=[rock_position], RelatingPropertyDefinition=rock_properties)
                last_pos = pos
    # Write the IFC file to disk
    file.write(scenario_name + ".ifc")

