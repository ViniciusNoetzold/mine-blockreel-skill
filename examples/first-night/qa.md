# Revisão de Primeira Noite

A folha de contato reuniu 56 quadros dos 33 planos. O percurso final foi checado a cada 0,05 s e ficou sem colisões de câmera ou personagens.

- A órbita mostra o personagem também de costas. A saída da bancada preserva a direção da corrida.
- Os planos de coleta e reação cortam parte do corpo de propósito para manter o objeto ou os olhos em destaque.
- O sol e a aranha recebem planos próprios. O jogador fica fora do quadro nesses insertos, assim como a aranha no contraplano.
- O abrigo conserva uma fresta fria e uma silhueta legível antes da tocha. A receita abre apenas durante a criação. O corte final alterna o Creeper com a reação do jogador.
- O último bloco fecha a entrada antes da troca para o interior. O teste de trajetória da versão final confirmou que o jogador e a câmera passam pela abertura no momento em que os blocos já foram removidos.

O primeiro passe encontrou colisões na corrida e um alerta falso em um bloco que já havia sido removido. A passagem foi liberada e a checagem por quadro agora lê o estado dos blocos no instante do plano. O teste da malha também cobre relevo com amplitude fracionária.

A verificação sonora foi feita por amostras e níveis. O WAV de origem tem uma pausa de um segundo de 56,25 a 57,25 s, seguida do estopim. A explosão começa com o corte para preto em 59,25 s.

O primeiro master em GPU perdeu materiais do cenário no trecho noturno, embora o MP4 tivesse a duração correta. Re-renderizei a partir do corte em 29,625 s por software e preservei a faixa de áudio. Revisei o plano da tocha no MP4 corrigido. O FFmpeg decodificou todo o arquivo e confirmou o primeiro preto contínuo aos 59,25 s. O master tem 1.440 quadros, 1280 × 720 a 24 fps e AAC estéreo, com 60,000 s de duração.
