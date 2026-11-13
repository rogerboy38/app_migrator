-- Pre-delete count (forensic baseline)
SELECT 'PRE-DELETE: tabWorkspace Sidebar Item rows pointing at Repost Accounting Ledger Settings' AS phase, COUNT(*) AS n
  FROM `tabWorkspace Sidebar Item`
  WHERE link_type='DocType' AND link_to='Repost Accounting Ledger Settings';

-- Surgical delete (exact 2 rows)
DELETE FROM `tabWorkspace Sidebar Item`
  WHERE link_type='DocType'
    AND link_to='Repost Accounting Ledger Settings'
    AND name IN ('71240vkm07', '79su7selqq');

-- Post-delete verification
SELECT 'POST-DELETE: should be 0' AS phase, COUNT(*) AS n
  FROM `tabWorkspace Sidebar Item`
  WHERE link_type='DocType' AND link_to='Repost Accounting Ledger Settings';
