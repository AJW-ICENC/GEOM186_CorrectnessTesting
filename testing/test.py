

import pyodbc
import pandas as pd
import geopandas as gpd
from shapely import wkt
import configparser



def main():

    ## -------Import Data----------

    ## ---------Query db set-up------------

    # Read database parameters
    config = configparser.ConfigParser()
    config.read("config.ini")

    server = config["database"]["server"]
    database = config["database"]["database"]
    username = config["database"]["username"]
    password = config["database"]["password"]
    driver = '{ODBC Driver 17 for SQL Server}'
    DMDconnection_string = f'''
        DRIVER={driver};
        SERVER={server};
        DATABASE={database};
        UID={username};
        PWD={password};
        Encrypt=yes;
        TrustServerCertificate=no;
        Connection Timeout=30;
    '''

    database = 'GapsAndOverlaps-UAT'

    GaOsconnection_string = f'''
        DRIVER={driver};
        SERVER={server};
        DATABASE={database};
        UID={username};
        PWD={password};
        Encrypt=yes;
        TrustServerCertificate=no;
        Connection Timeout=30;
    '''

    # SQL Query
    query_DMD = '''
    SELECT 
        [ID], 
        [Name], 
        [UsageBand], 
        [ModificationID], 
        [Scale], 
        [Edition], 
        [RegisteredAt] 
    FROM dbo.CellWorkItem 
    WHERE 
        ModificationID <> 3
    	AND CellStandardID = 1
        AND CAST(RegisteredAt AS DATE) >= CAST(DATEADD(DAY, -7, GETDATE()) AS DATE)
        AND CAST(RegisteredAt AS DATE) < CAST(GETDATE() AS DATE);

    '''
    
    query_GaO = """
    SELECT [ID]
        ,[CellWorkItemID_1]
        ,[CellName_1]
        ,[Scale_1]
        ,[UsageBand_1]
        ,[ModificationID_1]
        ,[Edition_1]
        ,[CellWorkItemID_2]
        ,[CellName_2]
        ,[Scale_2]
        ,[UsageBand_2]
        ,[ModificationID_2]
        ,[Edition_2]
        ,[NameJoin]
        ,[OverlapID]
        ,[OverlapStatus]
        ,[Comments]
        ,shape.STAsText() as geometry_wkt
    	,shape.STSrid as srid
    FROM [GapsAndOverlaps-UAT].[dbo].[S57Overlaps]
    """

    # initialize dfs
    df_DMD = None
    df_GaO = None
    gdf_qgis = None


    # read in Live shapefile

    gdf_qgis = gpd.read_file(r"V:\MANAGEMENT\IC-ENC Graphical Catalogue\In work\Model Inputs\POTENTIAL_OVERLAPS.shp")

    
    # Connect to dbs
    try:
        # Establish SQL db connections for DMD and GaOs
        with pyodbc.connect(DMDconnection_string) as conn_DMD, \
            pyodbc.connect(GaOsconnection_string) as conn_GaO:

            #query and Read to Dataframes
            df_DMD = pd.read_sql(query_DMD, conn_DMD)
            df_GaO = pd.read_sql(query_GaO, conn_GaO)

            # convert wkt shapely object
            df_GaO['geometry'] = df_GaO['geometry_wkt'].apply(wkt.loads)

            # Get the SRID from the first row
            if 'srid' in df_GaO.columns and not df_GaO.empty:
                srid = df_GaO['srid'].iloc[0]
                # print(f"Detected SRID: {srid}")
            else:
                srid = None
                print("Warning: SRID not found in data")
                raise("df_GaO is empty")
            
            # Drop unnecessary columns
            df_GaO = df_GaO.drop(columns=['geometry_wkt', 'shape', 'srid'], errors='ignore')
            
            # Create GeoDataFrame
            gdf_GaO = gpd.GeoDataFrame(df_GaO, geometry='geometry')

            # Set CRS based on SRID from SQL Server
            if srid:
                try:
                    gdf_GaO.set_crs(epsg=srid, inplace=True)
                    # print(f"CRS set to EPSG:{srid}")
                except Exception as e:
                    print(f"Could not set CRS for EPSG:{srid} - {e}")
                    print("You may need to set it manually")
            else:
                print("WARNING: No CRS set. Set it manually if you know the coordinate system:")

            
            print("Read completed")

    except Exception as e:
        raise("Connection failed:", e)



main()