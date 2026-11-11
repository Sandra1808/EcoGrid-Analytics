package EcoGrid.dao;

import EcoGrid.entity.Impactodesviacione;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

public interface ImpactodesviacioneRepository
        extends JpaRepository<Impactodesviacione, Long> {

    @Query("""
            select sum(i.costedesvioestimadoeur)
            from Impactodesviacione i
            where i.idccaa.id = :ccaaId
              and i.idtiempo.fechora between :desde and :hasta
            """)
    BigDecimal sumarCosteDesvio(
            @Param("ccaaId") Long ccaaId,
            @Param("desde") LocalDateTime desde,
            @Param("hasta") LocalDateTime hasta);

    List<Impactodesviacione>
    findByIdccaa_IdAndIdtiempo_FechoraBetweenOrderByIdtiempo_FechoraAsc(
            Long ccaaId, LocalDateTime desde, LocalDateTime hasta);
}