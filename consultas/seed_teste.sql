-- Dados de teste. Pode ser reexecutado: limpa antes de inserir.
TRUNCATE autor, acordo, documento CASCADE;

INSERT INTO autor (id, nome, email, telefone, endereco, empresa_nome, empresa_segmento) VALUES
 (1, 'Ana Silva',    'ana@exemplo.com',    '11 99999-0001', 'Rua A, Apto 1 - São Paulo - 01000-000',     'Empresa A', 'varejo'),
 (2, 'Bruno Costa',  'bruno@exemplo.com',  '21 99999-0002', 'Rua B, Apto 2 - Rio de Janeiro - 20000-000', 'Empresa B', 'serviços'),
 (3, 'Carla Dias',   'carla@exemplo.com',  '31 99999-0003', 'Rua C, Apto 3 - Belo Horizonte - 30000-000', 'Empresa C', 'indústria');

INSERT INTO acordo (id, autor_id, titulo) VALUES
 (1, 1, 'Acordo 1'),
 (2, 1, 'Acordo 2'),
 (3, 1, 'Acordo 3'),
 (4, 2, 'Acordo 4');

INSERT INTO documento (id, acordo_id, titulo, url, thumbnail_url) VALUES
 (1, 1, 'Termo de acordo',  'https://exemplo.com/1.png', 'https://exemplo.com/t1.png'),
 (2, 1, 'Minuta',           'https://exemplo.com/2.png', 'https://exemplo.com/t2.png'),
 (3, 1, 'Comprovante',      'https://exemplo.com/3.png', 'https://exemplo.com/t3.png'),
 (4, 2, 'Termo de acordo',  'https://exemplo.com/4.png', 'https://exemplo.com/t4.png'),
 (5, 2, 'Petição',          'https://exemplo.com/5.png', 'https://exemplo.com/t5.png'),
 (6, 4, 'Termo de acordo',  'https://exemplo.com/6.png', 'https://exemplo.com/t6.png');
