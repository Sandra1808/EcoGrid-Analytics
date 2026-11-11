package EcoGrid.dao;

import EcoGrid.entity.Demandageneracionree;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

public interface DemandageneracionreeRepository
        extends JpaRepository<Demandageneracionree, Long> {

    @EntityGraph(attributePaths = "idtiempo")
    List<Demandageneracionree>
    findByIdccaa_IdAndIdtiempo_FechoraBetweenOrderByIdtiempo_FechoraAsc(
            Long idccaa, LocalDateTime desde, LocalDateTime hasta);

    @EntityGraph(attributePaths = "idtiempo")
    Optional<Demandageneracionree>
    findFirstByIdccaa_IdOrderByIdtiempo_FechoraDesc(Long idccaa);
}