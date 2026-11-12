package EcoGrid.dao;

import EcoGrid.entity.Prediccionesdemanda;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

public interface PrediccionesdemandaRepository
        extends JpaRepository<Prediccionesdemanda, Long> {

    Optional<Prediccionesdemanda> findByIdmodelo_IdAndIdccaa_IdAndIdtiempo_Id(
            Long modeloId, Long ccaaId, Long tiempoId);

    @EntityGraph(attributePaths = "idtiempo")
    List<Prediccionesdemanda>
    findByIdccaa_IdAndIdtiempo_FechoraBetweenOrderByIdtiempo_FechoraAsc(
            Long ccaaId, LocalDateTime desde, LocalDateTime hasta);

    @EntityGraph(attributePaths = "idtiempo")
    Optional<Prediccionesdemanda>
    findFirstByIdccaa_IdOrderByIdtiempo_FechoraDesc(Long ccaaId);
}