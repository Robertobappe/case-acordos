-- 1) Quantidade de acordos e documentos por autor
--    LEFT JOIN: inclui autores sem acordos.
--    COUNT(DISTINCT ac.id): os JOINs multiplicam linhas, então conta cada acordo uma vez.
--    COUNT(d.id) ignora NULL, então acordos sem documento não inflam a contagem.
SELECT a.id,
       a.nome,
       COUNT(DISTINCT ac.id) AS qtd_acordos,
       COUNT(d.id)           AS qtd_documentos
FROM autor a
LEFT JOIN acordo ac   ON ac.autor_id = a.id
LEFT JOIN documento d ON d.acordo_id = ac.id
GROUP BY a.id, a.nome
ORDER BY qtd_acordos DESC, a.id;

-- 2) Autores com maior volume de acordos (top 3)
--    INNER JOIN: só quem tem acordos entra no ranking.
SELECT a.id,
       a.nome,
       COUNT(ac.id) AS qtd_acordos
FROM autor a
JOIN acordo ac ON ac.autor_id = a.id
GROUP BY a.id, a.nome
ORDER BY qtd_acordos DESC, a.id
LIMIT 3;

-- 3) Acordos sem documentos (anti-join)
--    Qualidade de dados: acordos cadastrados que ainda não têm nenhum documento.
SELECT ac.id,
       ac.titulo,
       ac.autor_id
FROM acordo ac
LEFT JOIN documento d ON d.acordo_id = ac.id
WHERE d.id IS NULL;
