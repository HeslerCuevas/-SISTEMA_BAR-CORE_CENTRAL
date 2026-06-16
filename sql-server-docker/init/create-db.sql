IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'Core_Master_DB')
BEGIN
    CREATE DATABASE Core_Master_DB;
END
GO
