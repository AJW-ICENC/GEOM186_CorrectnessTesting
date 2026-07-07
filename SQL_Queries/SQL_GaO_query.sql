SELECT [ID]
      ,[CellWorkItemID]
      ,[CellName]
      ,[Scale]
      ,[UsageBand]
      ,[ModificationID]
      ,[Edition]
      ,[ValidationStatusID]
      ,[RegisteredAt]
      ,[OverlapsCreated]
      ,shape.STAsText() as geometry_wkt
	  ,shape.STSrid as srid
  FROM [dbo].[S57CellWorkItem]
     WHERE 
        CAST(RegisteredAt AS DATE) >= CAST(DATEADD(DAY, -7, GETDATE()) AS DATE)
        AND CAST(RegisteredAt AS DATE) < CAST(GETDATE() AS DATE);
