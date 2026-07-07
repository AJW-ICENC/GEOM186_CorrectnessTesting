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
