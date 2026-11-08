SELECT CONCAT(
  'SELECT ''', TABLE_NAME, ''' src, ''', COLUMN_NAME, ''' col, name, `', COLUMN_NAME, '` ref FROM `', TABLE_NAME,
  '` WHERE `', COLUMN_NAME,
  '` IN (''Repost Accounting Ledger Settings'',''Label Management'',''TDS Default Parameter'',''BOM Scrap Item'',''Job Card Scrap Item'',''Subcontracting Inward Order Scrap Item'');'
) AS q
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME LIKE 'tab%'
  AND COLUMN_NAME IN (
    'doctype','doc_type','dt','ref_doctype','reference_doctype','reference_document',
    'link_to','link_doctype','document_type','target_doctype',
    'allow_doctype','child_doctype','parent_doctype','share_doctype',
    'allow','for_value','allowed_doctype','source_doctype','destination_doctype',
    'meta_doctype','referenced_doctype','document_doctype',
    'number_card_name','chart_name'
  )
ORDER BY TABLE_NAME, COLUMN_NAME;
